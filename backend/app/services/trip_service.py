"""Trip 业务服务。"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

from pydantic import BaseModel

from app.agent import MiniAgent, ToolRegistry
from app.agent.contracts import ToolTrace
from app.agent.workflows import TripWorkflow
from app.core import AppError, ExternalServiceError, ValidationError
from app.integrations import build_llm_client
from app.schemas import (
    Attraction,
    Budget,
    DayPlan,
    Hotel,
    Location,
    Meal,
    TripPlan,
    TripRequest,
    WeatherInfo,
)
from app.services.map_service import get_map_service
from app.services.photo_service import get_photo_service

_HOTEL_KEYWORDS = ("酒店", "宾馆", "民宿", "客栈", "青旅", "住宿")
_MEAL_KEYWORDS = ("餐厅", "小吃", "早餐", "午餐", "晚餐", "饭店", "美食 餐厅")


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


def _estimate_hotel_cost(accommodation: str) -> int:
    text = accommodation or ""
    if "豪华" in text or "高端" in text or "五星" in text:
        return 880
    if "经济" in text or "青旅" in text or "民宿" in text:
        return 320
    return 480


def _default_meals(day_index: int) -> List[Meal]:
    label = f"第{day_index + 1}天"
    return [
        Meal(type="breakfast", name=f"{label}早餐", description="本地早餐推荐", estimated_cost=25),
        Meal(type="lunch", name=f"{label}午餐", description="午餐推荐", estimated_cost=45),
        Meal(type="dinner", name=f"{label}晚餐", description="晚餐推荐", estimated_cost=70),
    ]


def _build_base_plan(request: TripRequest, *, suggestions: str) -> TripPlan:
    """构造基础行程。"""
    days: List[DayPlan] = []
    weather_info: List[WeatherInfo] = []
    default_hotel_cost = _estimate_hotel_cost(request.accommodation)

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
                    estimated_cost=default_hotel_cost,
                ),
                attractions=[],
                meals=_default_meals(idx),
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
        total_hotels=default_hotel_cost * request.travel_days,
        total_meals=sum(meal.estimated_cost for day in days for meal in day.meals),
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


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _parse_location(raw: Any) -> Location:
    if isinstance(raw, dict):
        return Location(
            longitude=_to_float(raw.get("longitude", raw.get("lon", 0.0))),
            latitude=_to_float(raw.get("latitude", raw.get("lat", 0.0))),
        )
    if isinstance(raw, str) and "," in raw:
        lon, lat = raw.split(",", 1)
        return Location(longitude=_to_float(lon), latitude=_to_float(lat))
    return Location(longitude=0.0, latitude=0.0)


def _parse_ticket_price(item: Dict[str, Any]) -> int:
    for key in ("ticket_price", "cost", "price"):
        if key in item:
            value = _to_int(item.get(key), 0)
            if value > 0:
                return value
    return 60


def _looks_like_hotel_trace(trace: ToolTrace) -> bool:
    if trace.tool_name != "search_poi":
        return False
    keywords = str(trace.arguments.get("keywords", "")).lower()
    return any(token in keywords for token in _HOTEL_KEYWORDS)


def _looks_like_meal_trace(trace: ToolTrace) -> bool:
    if trace.tool_name != "search_poi":
        return False
    keywords = str(trace.arguments.get("keywords", "")).lower()
    return any(token in keywords for token in _MEAL_KEYWORDS)


def _extract_photo_map(traces: List[ToolTrace]) -> Dict[str, str]:
    photo_map: Dict[str, str] = {}
    for trace in traces:
        if trace.tool_name != "get_photo" or not isinstance(trace.result, dict):
            continue
        name = trace.result.get("name")
        photo_url = trace.result.get("photo_url")
        if isinstance(name, str) and name and isinstance(photo_url, str) and photo_url:
            photo_map[name] = photo_url
    return photo_map


def _apply_weather(plan: TripPlan, weather_items: List[Dict[str, Any]]) -> None:
    if not weather_items:
        return

    weather_result: List[WeatherInfo] = []
    for idx, day in enumerate(plan.days):
        item = weather_items[idx] if idx < len(weather_items) else {}
        if not isinstance(item, dict):
            item = {}
        weather_result.append(
            WeatherInfo(
                date=str(item.get("date", day.date)),
                day_weather=str(item.get("day_weather", item.get("dayweather", ""))),
                night_weather=str(item.get("night_weather", item.get("nightweather", ""))),
                day_temp=item.get("day_temp", item.get("daytemp", 0)),
                night_temp=item.get("night_temp", item.get("nighttemp", 0)),
                wind_direction=str(item.get("wind_direction", item.get("daywind", ""))),
                wind_power=str(item.get("wind_power", item.get("daypower", ""))),
            )
        )
    plan.weather_info = weather_result


def _build_attractions(
    items: List[Dict[str, Any]],
    *,
    photo_map: Dict[str, str],
) -> List[Attraction]:
    attractions: List[Attraction] = []
    for item in items:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        photo_url = photo_map.get(name)
        attractions.append(
            Attraction(
                name=name,
                address=str(item.get("address", "")),
                location=_parse_location(item.get("location")),
                visit_duration=120,
                description=f"推荐景点：{name}",
                category=str(item.get("type", item.get("typecode", "景点"))),
                ticket_price=_parse_ticket_price(item),
                poi_id=str(item.get("id", "")),
                image_url=photo_url,
                photos=[photo_url] if photo_url else [],
            )
        )
    return attractions


def _apply_attractions(plan: TripPlan, attractions: List[Attraction]) -> None:
    for day in plan.days:
        day.attractions = []
    if not attractions or not plan.days:
        return

    max_count = len(plan.days) * 3
    selected = attractions[:max_count]
    for idx, attraction in enumerate(selected):
        day_idx = min(idx // 3, len(plan.days) - 1)
        plan.days[day_idx].attractions.append(attraction)


def _apply_hotels(plan: TripPlan, hotel_items: List[Dict[str, Any]], accommodation: str) -> None:
    if not plan.days:
        return
    if not hotel_items:
        return

    first = hotel_items[0]
    if not isinstance(first, dict):
        return

    hotel = Hotel(
        name=str(first.get("name", f"{plan.city}推荐酒店")),
        address=str(first.get("address", "")),
        location=_parse_location(first.get("location")),
        type=accommodation,
        estimated_cost=_estimate_hotel_cost(accommodation),
        rating=str(first.get("rating", "")),
        distance=str(first.get("distance", "")),
    )
    for day in plan.days:
        day.hotel = hotel


def _meal_type_label(meal_type: str) -> str:
    mapping = {
        "breakfast": "早餐",
        "lunch": "午餐",
        "dinner": "晚餐",
    }
    return mapping.get(meal_type, meal_type)


def _meal_cost_by_type(meal_type: str) -> int:
    mapping = {"breakfast": 25, "lunch": 45, "dinner": 70}
    return mapping.get(meal_type, 40)


def _apply_meals(plan: TripPlan, meal_items: List[Dict[str, Any]]) -> None:
    if not plan.days or not meal_items:
        return

    candidates: List[Dict[str, Any]] = []
    for item in meal_items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        candidates.append(item)
    if not candidates:
        return

    meal_types = ("breakfast", "lunch", "dinner")
    for day_idx, day in enumerate(plan.days):
        assigned: List[Meal] = []
        for slot_idx, meal_type in enumerate(meal_types):
            candidate = candidates[(day_idx * len(meal_types) + slot_idx) % len(candidates)]
            name = str(candidate.get("name", "")).strip() or f"{_meal_type_label(meal_type)}推荐"
            estimated_cost = _to_int(candidate.get("cost", candidate.get("price", 0)), 0)
            if estimated_cost <= 0:
                estimated_cost = _meal_cost_by_type(meal_type)
            assigned.append(
                Meal(
                    type=meal_type,
                    name=name,
                    address=str(candidate.get("address", "")) or None,
                    location=_parse_location(candidate.get("location")),
                    description=f"{_meal_type_label(meal_type)}推荐：{name}",
                    estimated_cost=estimated_cost,
                )
            )
        day.meals = assigned


def _estimate_transport_cost(traces: List[ToolTrace], day_count: int) -> int:
    distance_total = 0.0
    for trace in traces:
        if trace.tool_name != "plan_route" or not isinstance(trace.result, dict):
            continue
        distance_total += _to_float(trace.result.get("distance", 0.0), 0.0)

    if distance_total <= 0:
        return 50 * day_count

    # 按公里估算日均交通费用，并设置保底值避免过低。
    estimated = int((distance_total / 1000.0) * 8)
    return max(35 * day_count, estimated)


def _recalculate_budget(plan: TripPlan, traces: List[ToolTrace]) -> None:
    total_attractions = sum(item.ticket_price for day in plan.days for item in day.attractions)
    total_hotels = sum((day.hotel.estimated_cost if day.hotel else 0) for day in plan.days)
    total_meals = sum(meal.estimated_cost for day in plan.days for meal in day.meals)
    total_transportation = _estimate_transport_cost(traces, len(plan.days))
    plan.budget = Budget(
        total_attractions=total_attractions,
        total_hotels=total_hotels,
        total_meals=total_meals,
        total_transportation=total_transportation,
        total=total_attractions + total_hotels + total_meals + total_transportation,
    )


def _apply_tool_traces(plan: TripPlan, traces: List[ToolTrace], request: TripRequest) -> None:
    """将工具调用结果映射回 TripPlan。"""
    weather_items: List[Dict[str, Any]] = []
    attraction_items: List[Dict[str, Any]] = []
    hotel_items: List[Dict[str, Any]] = []
    meal_items: List[Dict[str, Any]] = []
    photo_map = _extract_photo_map(traces)

    for trace in traces:
        if trace.tool_name == "get_weather" and isinstance(trace.result, list):
            weather_items = [item for item in trace.result if isinstance(item, dict)]

        if trace.tool_name == "search_poi" and isinstance(trace.result, list):
            items = [item for item in trace.result if isinstance(item, dict)]
            if _looks_like_hotel_trace(trace):
                hotel_items.extend(items)
            elif _looks_like_meal_trace(trace):
                meal_items.extend(items)
            else:
                attraction_items.extend(items)

    _apply_weather(plan, weather_items)
    attractions = _build_attractions(attraction_items, photo_map=photo_map)
    _apply_attractions(plan, attractions)
    _apply_hotels(plan, hotel_items, request.accommodation)
    _apply_meals(plan, meal_items)

    # 若只有一张图片且未命中名称，兜底挂到首个景点。
    if photo_map and plan.days and plan.days[0].attractions:
        if not plan.days[0].attractions[0].image_url:
            first_url = next(iter(photo_map.values()))
            plan.days[0].attractions[0].image_url = first_url
            plan.days[0].attractions[0].photos = [first_url]

    _recalculate_budget(plan, traces)


def _build_tool_registry() -> ToolRegistry:
    map_service = get_map_service()
    photo_service = get_photo_service()
    registry = ToolRegistry()

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
    return registry


async def _build_plan_without_llm(request: TripRequest, registry: ToolRegistry) -> TripPlan:
    plan = _build_base_plan(request, suggestions="LLM 未配置，已按规则完成工具编排。")
    traces: List[ToolTrace] = []

    async def _dispatch(tool_name: str, args: Dict[str, Any]) -> Any | None:
        try:
            result = await registry.dispatch(tool_name, args)
        except (AppError, ExternalServiceError):
            return None
        traces.append(ToolTrace(tool_name=tool_name, arguments=args, result=result))
        return result

    attractions = await _dispatch(
        "search_poi",
        {
            "keywords": request.preferences[0] if request.preferences else "热门景点",
            "city": request.city,
            "citylimit": True,
        },
    )
    await _dispatch("get_weather", {"city": request.city})
    await _dispatch(
        "search_poi",
        {
            "keywords": request.accommodation or "酒店",
            "city": request.city,
            "citylimit": True,
        },
    )
    await _dispatch(
        "search_poi",
        {
            "keywords": "美食 餐厅",
            "city": request.city,
            "citylimit": True,
        },
    )

    first_name = ""
    if isinstance(attractions, list):
        for item in attractions:
            if isinstance(item, dict) and isinstance(item.get("name"), str) and item["name"]:
                first_name = item["name"]
                break
    if first_name:
        await _dispatch("get_photo", {"name": first_name})

    _apply_tool_traces(plan, traces, request)
    return plan


async def build_trip_plan(request: TripRequest) -> TripPlan:
    """构造 TripPlan，并在可用时接入 MiniAgent 工作流。"""
    base_plan = _build_base_plan(
        request,
        suggestions="当前为基础行程。若配置了 LLM，将自动补全工具调用建议。",
    )
    registry = _build_tool_registry()

    try:
        llm_client = build_llm_client()
    except ValidationError:
        return await _build_plan_without_llm(request, registry)

    agent = MiniAgent(llm_client=llm_client, tool_registry=registry, max_steps=6)
    workflow = TripWorkflow(agent)

    try:
        result = await workflow.run(request)
    except (ExternalServiceError, AppError):
        return await _build_plan_without_llm(request, registry)

    _apply_tool_traces(base_plan, result.traces, request)
    if result.content:
        base_plan.overall_suggestions = result.content
    return base_plan
