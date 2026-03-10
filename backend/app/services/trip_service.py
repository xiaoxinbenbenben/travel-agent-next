"""Trip 业务服务。"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
import json
import logging
from time import perf_counter
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from app.agent import MiniAgent, ToolRegistry
from app.agent.contracts import ToolTrace
from app.agent.workflows import TripWorkflow
from app.core import AppError, ExternalServiceError, ValidationError, log_duration
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
logger = logging.getLogger(__name__)


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


class _PlannerMealNames(BaseModel):
    breakfast: str | None = None
    lunch: str | None = None
    dinner: str | None = None


class _PlannerDayItem(BaseModel):
    day_index: int
    theme: str | None = None
    description: str | None = None
    attraction_poi_ids: List[str] = Field(default_factory=list)
    meal_names: _PlannerMealNames | None = None
    hotel_name: str | None = None


class _PlannerResult(BaseModel):
    days: List[_PlannerDayItem] = Field(default_factory=list)
    overall_suggestions: str | None = None


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


def _normalized_preferences(preferences: List[str]) -> List[str]:
    normalized: List[str] = []
    for item in preferences:
        value = item.strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized or ["热门景点"]


def _display_theme(theme: str) -> str:
    return "城市漫游" if theme == "热门景点" else theme


def _day_theme(preferences: List[str], day_index: int) -> str:
    themes = _normalized_preferences(preferences)
    return themes[day_index % len(themes)]


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
                description=f"第{idx + 1}天建议以{_display_theme(_day_theme(request.preferences, idx))}为主题。",
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


def _extract_json_text(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()
    return text


def _parse_planner_result(raw_content: str) -> _PlannerResult | None:
    text = _extract_json_text(raw_content)
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    try:
        return _PlannerResult.model_validate(payload)
    except Exception:
        return None


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
        fallback = plan.weather_info[idx] if idx < len(plan.weather_info) else WeatherInfo(date=day.date)
        weather_result.append(
            WeatherInfo(
                date=day.date,
                day_weather=str(
                    item.get("day_weather", item.get("dayweather", fallback.day_weather))
                ),
                night_weather=str(
                    item.get("night_weather", item.get("nightweather", fallback.night_weather))
                ),
                day_temp=item.get("day_temp", item.get("daytemp", fallback.day_temp)),
                night_temp=item.get("night_temp", item.get("nighttemp", fallback.night_temp)),
                wind_direction=str(item.get("wind_direction", item.get("daywind", fallback.wind_direction))),
                wind_power=str(item.get("wind_power", item.get("daypower", fallback.wind_power))),
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


def _attraction_identity(attraction: Attraction) -> str:
    return attraction.poi_id or f"{attraction.name}|{attraction.address}"


def _theme_keywords(theme: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    normalized = theme.strip()
    if "自然" in normalized or "景观" in normalized:
        return (
            ("自然", "景观", "公园", "湿地", "森林", "峡谷", "山", "湖", "保护区", "长城"),
            ("博物", "博物馆", "故宫", "国子监", "胡同", "文化", "古", "遗址", "牌坊", "斜街", "街", "宫", "坛", "天坛"),
        )
    if "历史" in normalized or "文化" in normalized:
        return (
            ("历史", "文化", "博物", "故宫", "胡同", "遗址", "古", "牌坊", "街", "馆", "宫", "坛", "长城"),
            ("湿地", "森林", "峡谷", "保护区"),
        )
    return ((), ())


def _theme_relevance_score(theme: str, attraction: Attraction) -> int:
    positive_keywords, negative_keywords = _theme_keywords(theme)
    if not positive_keywords and not negative_keywords:
        return 0

    haystack = " ".join(
        part
        for part in (
            attraction.name,
            attraction.category or "",
            attraction.description,
            attraction.address,
        )
        if part
    )
    score = 0
    if theme and theme in haystack:
        score += 4
    score += sum(2 for keyword in positive_keywords if keyword and keyword in haystack)
    score -= sum(3 for keyword in negative_keywords if keyword and keyword in haystack)
    return score


def _dedupe_attractions(attractions: List[Attraction]) -> List[Attraction]:
    deduped: List[Attraction] = []
    seen: set[str] = set()
    for attraction in attractions:
        identity = _attraction_identity(attraction)
        if identity in seen:
            continue
        seen.add(identity)
        deduped.append(attraction)
    return deduped


def _prioritize_attractions_for_theme(theme: str, attractions: List[Attraction]) -> List[Attraction]:
    deduped = _dedupe_attractions(attractions)
    scored = [(_theme_relevance_score(theme, attraction), attraction) for attraction in deduped]
    if not scored:
        return []

    scored.sort(key=lambda item: item[0], reverse=True)
    if any(score > 0 for score, _ in scored):
        filtered = [attraction for score, attraction in scored if score >= 0]
        if filtered:
            return filtered
    return [attraction for _, attraction in scored]


def _take_attractions(pool: List[Attraction], *, used: set[str], limit: int) -> List[Attraction]:
    selected: List[Attraction] = []
    while pool and len(selected) < limit:
        attraction = pool.pop(0)
        identity = _attraction_identity(attraction)
        if identity in used:
            continue
        used.add(identity)
        selected.append(attraction)
    return selected


def _apply_attractions(
    plan: TripPlan,
    attractions_by_theme: Dict[str, List[Attraction]],
    preferences: List[str],
) -> None:
    for day in plan.days:
        day.attractions = []
    if not attractions_by_theme or not plan.days:
        return

    themed_pools = {
        theme: _prioritize_attractions_for_theme(theme, list(items))
        for theme, items in attractions_by_theme.items()
    }
    theme_schedule = [_day_theme(preferences, idx) for idx in range(len(plan.days))]
    remaining_days_by_theme = Counter(theme_schedule)
    used: set[str] = set()

    for day_idx, day in enumerate(plan.days):
        theme = theme_schedule[day_idx]
        pool = themed_pools.get(theme, [])
        remaining_days = max(remaining_days_by_theme.get(theme, 1), 1)
        remaining_items = len(pool)
        day_limit = 0
        if remaining_items > 0:
            day_limit = min(3, max(1, (remaining_items + remaining_days - 1) // remaining_days))
        day.attractions = _take_attractions(pool, used=used, limit=day_limit)
        remaining_days_by_theme[theme] -= 1


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


def _build_hotel_candidates(hotel_items: List[Dict[str, Any]], accommodation: str) -> List[Hotel]:
    candidates: List[Hotel] = []
    seen: set[str] = set()
    for item in hotel_items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        candidates.append(
            Hotel(
                name=name,
                address=str(item.get("address", "")),
                location=_parse_location(item.get("location")),
                type=accommodation,
                estimated_cost=_estimate_hotel_cost(accommodation),
                rating=str(item.get("rating", "")),
                distance=str(item.get("distance", "")),
            )
        )
    return candidates


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


def _meal_from_candidate(candidate: Dict[str, Any], meal_type: str) -> Meal:
    name = str(candidate.get("name", "")).strip() or f"{_meal_type_label(meal_type)}推荐"
    estimated_cost = _to_int(candidate.get("cost", candidate.get("price", 0)), 0)
    if estimated_cost <= 0:
        estimated_cost = _meal_cost_by_type(meal_type)
    return Meal(
        type=meal_type,
        name=name,
        address=str(candidate.get("address", "")) or None,
        location=_parse_location(candidate.get("location")),
        description=f"{_meal_type_label(meal_type)}推荐：{name}",
        estimated_cost=estimated_cost,
    )


def _estimate_transport_cost(day_count: int, transportation: str) -> int:
    transport = transportation or ""
    daily_cost = 50
    if "步行" in transport:
        daily_cost = 20
    elif "公共" in transport or "公交" in transport or "地铁" in transport:
        daily_cost = 35
    elif "打车" in transport or "出租" in transport or "网约车" in transport:
        daily_cost = 90
    elif "自驾" in transport or "租车" in transport:
        daily_cost = 120
    return daily_cost * day_count


def _recalculate_budget(plan: TripPlan, request: TripRequest) -> None:
    total_attractions = sum(item.ticket_price for day in plan.days for item in day.attractions)
    total_hotels = sum((day.hotel.estimated_cost if day.hotel else 0) for day in plan.days)
    total_meals = sum(meal.estimated_cost for day in plan.days for meal in day.meals)
    total_transportation = _estimate_transport_cost(len(plan.days), request.transportation)
    plan.budget = Budget(
        total_attractions=total_attractions,
        total_hotels=total_hotels,
        total_meals=total_meals,
        total_transportation=total_transportation,
        total=total_attractions + total_hotels + total_meals + total_transportation,
    )


def _extract_trace_payloads(
    traces: List[ToolTrace],
) -> tuple[
    List[Dict[str, Any]],
    Dict[str, List[Dict[str, Any]]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    Dict[str, str],
]:
    weather_items: List[Dict[str, Any]] = []
    attraction_items_by_theme: Dict[str, List[Dict[str, Any]]] = {}
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
                theme = str(trace.arguments.get("keywords", "")).strip() or "热门景点"
                attraction_items_by_theme.setdefault(theme, []).extend(items)

    return weather_items, attraction_items_by_theme, hotel_items, meal_items, photo_map


def _build_attraction_lookup(attractions_by_theme: Dict[str, List[Attraction]]) -> Dict[str, Attraction]:
    lookup: Dict[str, Attraction] = {}
    for attractions in attractions_by_theme.values():
        for attraction in attractions:
            if attraction.poi_id:
                lookup[attraction.poi_id] = attraction
            lookup.setdefault(attraction.name, attraction)
    return lookup


def _build_meal_lookup(meal_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    for item in meal_items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if name and name not in lookup:
            lookup[name] = item
    return lookup


def _apply_planner_result(
    plan: TripPlan,
    planner_result: _PlannerResult,
    attractions_by_theme: Dict[str, List[Attraction]],
    hotel_items: List[Dict[str, Any]],
    meal_items: List[Dict[str, Any]],
    request: TripRequest,
) -> str | None:
    attraction_lookup = _build_attraction_lookup(attractions_by_theme)
    hotel_lookup = {hotel.name: hotel for hotel in _build_hotel_candidates(hotel_items, request.accommodation)}
    meal_lookup = _build_meal_lookup(meal_items)
    applied_any = False

    for item in planner_result.days:
        if item.day_index < 0 or item.day_index >= len(plan.days):
            continue
        day = plan.days[item.day_index]
        if item.description:
            day.description = item.description

        selected_attractions = [
            attraction_lookup[key]
            for key in item.attraction_poi_ids
            if key in attraction_lookup
        ]
        if selected_attractions:
            day.attractions = [attraction.model_copy(deep=True) for attraction in selected_attractions[:3]]
            applied_any = True

        if item.hotel_name and item.hotel_name in hotel_lookup:
            day.hotel = hotel_lookup[item.hotel_name].model_copy(deep=True)

        if item.meal_names:
            updated_meals: List[Meal] = []
            for meal_type in ("breakfast", "lunch", "dinner"):
                meal_name = getattr(item.meal_names, meal_type)
                candidate = meal_lookup.get(meal_name or "")
                if candidate is not None:
                    updated_meals.append(_meal_from_candidate(candidate, meal_type))
                else:
                    existing = next((meal for meal in day.meals if meal.type == meal_type), None)
                    updated_meals.append(existing.model_copy(deep=True) if existing is not None else _default_meals(day.day_index)[("breakfast", "lunch", "dinner").index(meal_type)])
            day.meals = updated_meals

    if not applied_any:
        return None
    if planner_result.overall_suggestions:
        return planner_result.overall_suggestions
    return None


def _apply_tool_traces(
    plan: TripPlan,
    traces: List[ToolTrace],
    request: TripRequest,
    *,
    planner_content: str = "",
) -> str | None:
    """将工具调用结果映射回 TripPlan。"""
    (
        weather_items,
        attraction_items_by_theme,
        hotel_items,
        meal_items,
        photo_map,
    ) = _extract_trace_payloads(traces)

    _apply_weather(plan, weather_items)
    attractions_by_theme = {
        theme: _build_attractions(items, photo_map=photo_map)
        for theme, items in attraction_items_by_theme.items()
    }
    _apply_attractions(plan, attractions_by_theme, request.preferences)
    _apply_hotels(plan, hotel_items, request.accommodation)
    _apply_meals(plan, meal_items)
    planner_result = _parse_planner_result(planner_content)
    planner_suggestions = None
    if planner_result is not None:
        planner_suggestions = _apply_planner_result(
            plan,
            planner_result,
            attractions_by_theme,
            hotel_items,
            meal_items,
            request,
        )
    _apply_missing_photos(plan, photo_map)

    _recalculate_budget(plan, request)
    return planner_suggestions


def _build_overall_suggestions(plan: TripPlan, request: TripRequest) -> str:
    themes = "、".join(_display_theme(item) for item in _normalized_preferences(request.preferences))
    attraction_count = sum(len(day.attractions) for day in plan.days)
    weather = next(
        (item for item in plan.weather_info if item.day_weather or item.night_weather),
        None,
    )
    hotel_name = plan.days[0].hotel.name if plan.days and plan.days[0].hotel else f"{request.city}推荐酒店"

    summary = f"{request.city}{request.travel_days}天行程已围绕{themes}安排。"
    if attraction_count > 0:
        summary += f" 当前共纳入{attraction_count}个景点，便于按主题展开游玩。"
    if weather is not None:
        summary += f" 首日天气预计为{weather.day_weather or weather.night_weather}。"
    summary += f" 建议优先使用{request.transportation}串联行程，并以{hotel_name}作为落脚点。"
    summary += " 出发前再确认景点开放时间与酒店可订状态即可。"
    return summary


def _apply_missing_photos(plan: TripPlan, photo_map: Dict[str, str]) -> None:
    photo_service = get_photo_service()
    total_attractions = 0
    reused_photos = 0
    fetched_photos = 0

    with log_duration(
        logger,
        "图片补全",
        start_message="🖼️ 开始补全景点图片...",
        success_message="🖼️ 图片补全完成",
    ):
        for day in plan.days:
            for attraction in day.attractions:
                total_attractions += 1
                photo_url = attraction.image_url or photo_map.get(attraction.name)
                if photo_url:
                    reused_photos += 1
                else:
                    photo_url = photo_service.get_attraction_photo(attraction.name)
                    if photo_url:
                        fetched_photos += 1
                if not photo_url:
                    continue
                attraction.image_url = photo_url
                attraction.photos = [photo_url]
    logger.info(
        "🖼️ 图片补全统计 | 景点数=%d | 复用=%d | 外部查询成功=%d",
        total_attractions,
        reused_photos,
        fetched_photos,
    )


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

    for preference in _normalized_preferences(request.preferences):
        await _dispatch(
            "search_poi",
            {
                "keywords": preference,
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

    planner_suggestions = _apply_tool_traces(plan, traces, request)
    plan.overall_suggestions = planner_suggestions or _build_overall_suggestions(plan, request)
    return plan


async def build_trip_plan(request: TripRequest) -> TripPlan:
    """构造 TripPlan，并在可用时接入 MiniAgent 工作流。"""
    started_at = perf_counter()
    base_plan = _build_base_plan(
        request,
        suggestions="当前为基础行程。若配置了 LLM，将自动补全工具调用建议。",
    )
    registry = _build_tool_registry()

    try:
        llm_client = build_llm_client()
    except ValidationError:
        logger.warning("LLM 未配置，降级到规则编排")
        return await _build_plan_without_llm(request, registry)

    agent = MiniAgent(llm_client=llm_client, tool_registry=registry, max_steps=6)
    workflow = TripWorkflow(agent)

    try:
        with log_duration(
            logger,
            "TripPlan 构建",
            start_message="🔄 开始构建 TripPlan...",
        ):
            result = await workflow.run(request)
    except (ExternalServiceError, AppError):
        logger.exception("TripWorkflow 失败，降级到规则编排")
        return await _build_plan_without_llm(request, registry)

    planner_suggestions = _apply_tool_traces(
        base_plan,
        result.traces,
        request,
        planner_content=result.content,
    )
    base_plan.overall_suggestions = planner_suggestions or _build_overall_suggestions(base_plan, request)
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info("✅ TripPlan 构建完成 | traces=%d | 总耗时 %.2f ms", len(result.traces), elapsed_ms)
    return base_plan
