"""Trip 业务服务。"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

from pydantic import BaseModel

from app.agent import MiniAgent, ToolRegistry
from app.agent.workflows import TripWorkflow
from app.core import AppError, ExternalServiceError, ValidationError
from app.integrations import build_llm_client
from app.schemas import (
    Attraction,
    Budget,
    DayPlan,
    Hotel,
    Location,
    TripPlan,
    TripRequest,
    WeatherInfo,
)
from app.services.map_service import get_map_service
from app.services.photo_service import get_photo_service


class _SearchPOIArgs(BaseModel):
    keywords: str
    city: str
    citylimit: bool = True


class _WeatherArgs(BaseModel):
    city: str


class _RouteArgs(BaseModel):
    origin_address: str
    destination_address: str
    origin_city: str | None = None
    destination_city: str | None = None
    route_type: str = "walking"


class _PhotoArgs(BaseModel):
    name: str


def _day_date(start_date_text: str, day_index: int) -> str:
    try:
        start = date.fromisoformat(start_date_text)
        return (start + timedelta(days=day_index)).isoformat()
    except ValueError:
        return start_date_text


def _build_base_plan(request: TripRequest, *, suggestions: str) -> TripPlan:
    """构造基础行程。"""
    days: List[DayPlan] = []
    weather_info: List[WeatherInfo] = []

    for idx in range(request.travel_days):
        day_text = _day_date(request.start_date, idx)
        days.append(
            DayPlan(
                date=day_text,
                day_index=idx,
                description=f"第{idx + 1}天建议以{request.preferences[0] if request.preferences else '城市漫游'}为主题。",
                transportation=request.transportation,
                accommodation=request.accommodation,
                hotel=Hotel(
                    name=f"{request.city}精选酒店",
                    address=f"{request.city}市中心",
                    estimated_cost=380,
                ),
                attractions=[],
                meals=[],
            )
        )
        weather_info.append(
            WeatherInfo(
                date=day_text,
                day_weather="待查询",
                night_weather="待查询",
                day_temp=0,
                night_temp=0,
                wind_direction="",
                wind_power="",
            )
        )

    budget = Budget(
        total_attractions=0,
        total_hotels=380 * request.travel_days,
        total_meals=120 * request.travel_days,
        total_transportation=50 * request.travel_days,
    )
    budget.total = (
        budget.total_attractions
        + budget.total_hotels
        + budget.total_meals
        + budget.total_transportation
    )

    return TripPlan(
        city=request.city,
        start_date=request.start_date,
        end_date=request.end_date,
        days=days,
        weather_info=weather_info,
        overall_suggestions=suggestions,
        budget=budget,
    )


def _parse_location(raw: Any) -> Location:
    if isinstance(raw, dict):
        return Location(
            longitude=float(raw.get("longitude", 0.0)),
            latitude=float(raw.get("latitude", 0.0)),
        )
    if isinstance(raw, str) and "," in raw:
        lon, lat = raw.split(",", 1)
        try:
            return Location(longitude=float(lon), latitude=float(lat))
        except ValueError:
            pass
    return Location(longitude=0.0, latitude=0.0)


def _apply_tool_traces(plan: TripPlan, traces: list[Any]) -> None:
    """将工具调用结果映射回 TripPlan。"""
    for trace in traces:
        # 天气工具结果可直接覆盖 weather_info。
        if trace.tool_name == "get_weather" and isinstance(trace.result, list):
            weather = [WeatherInfo.model_validate(item) for item in trace.result]
            if weather:
                plan.weather_info = weather

        # 先把搜索到的 POI 折叠成首日景点，后续可升级为多日分配策略。
        if trace.tool_name == "search_poi" and isinstance(trace.result, list):
            attractions: List[Attraction] = []
            for item in trace.result[:3]:
                if not isinstance(item, dict):
                    continue
                attractions.append(
                    Attraction(
                        name=str(item.get("name", "未命名景点")),
                        address=str(item.get("address", "")),
                        location=_parse_location(item.get("location")),
                        visit_duration=120,
                        description=f"推荐景点：{item.get('name', '未命名景点')}",
                        category=str(item.get("type", "景点")),
                    )
                )
            if attractions and plan.days:
                plan.days[0].attractions = attractions

        # 图片工具结果用于补齐首个景点的 image_url。
        if trace.tool_name == "get_photo" and isinstance(trace.result, dict):
            photo_url = trace.result.get("photo_url")
            if isinstance(photo_url, str) and photo_url and plan.days and plan.days[0].attractions:
                plan.days[0].attractions[0].image_url = photo_url


async def build_trip_plan(request: TripRequest) -> TripPlan:
    """构造 TripPlan，并在可用时接入 MiniAgent 工作流。"""
    base_plan = _build_base_plan(
        request,
        suggestions="当前为基础行程。若配置了 LLM，将自动补全工具调用建议。",
    )

    try:
        llm_client = build_llm_client()
    except ValidationError:
        # 与旧系统兼容：LLM 未配置时仍返回可用基础行程，不让 API 直接失败。
        base_plan.overall_suggestions = "LLM 未配置，返回基础行程。"
        return base_plan

    map_service = get_map_service()
    photo_service = get_photo_service()
    registry = ToolRegistry()

    # ToolRegistry 中的工具由 MiniAgent 通过结构化调用驱动。
    async def _search_poi_tool(payload: Dict[str, Any]) -> list[Dict[str, Any]]:
        data = await map_service.search_poi(
            keywords=payload["keywords"],
            city=payload["city"],
            citylimit=payload.get("citylimit", True),
        )
        return [item.model_dump() for item in data]

    async def _weather_tool(payload: Dict[str, Any]) -> list[Dict[str, Any]]:
        data = await map_service.get_weather(payload["city"])
        return [item.model_dump() for item in data]

    async def _route_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
        data = await map_service.plan_route(
            origin_address=payload["origin_address"],
            destination_address=payload["destination_address"],
            origin_city=payload.get("origin_city"),
            destination_city=payload.get("destination_city"),
            route_type=payload.get("route_type", "walking"),
        )
        return data.model_dump()

    async def _photo_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"name": payload["name"], "photo_url": photo_service.get_attraction_photo(payload["name"])}

    registry.register("search_poi", _search_poi_tool, args_model=_SearchPOIArgs)
    registry.register("get_weather", _weather_tool, args_model=_WeatherArgs)
    registry.register("plan_route", _route_tool, args_model=_RouteArgs)
    registry.register("get_photo", _photo_tool, args_model=_PhotoArgs)

    agent = MiniAgent(llm_client=llm_client, tool_registry=registry, max_steps=5)
    workflow = TripWorkflow(agent)

    try:
        result = await workflow.run(request)
    except (ExternalServiceError, AppError):
        # 外部依赖波动时回退基础行程，保证接口可用性。
        base_plan.overall_suggestions = "LLM 或工具调用暂不可用，返回基础行程。"
        return base_plan

    _apply_tool_traces(base_plan, result.traces)
    if result.content:
        base_plan.overall_suggestions = result.content
    return base_plan
