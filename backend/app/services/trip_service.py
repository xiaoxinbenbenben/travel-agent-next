"""Trip 业务服务。"""

from __future__ import annotations

from datetime import date, timedelta

from app.schemas import Budget, DayPlan, Hotel, TripPlan, TripRequest, WeatherInfo


def _day_date(start_date_text: str, day_index: int) -> str:
    try:
        start = date.fromisoformat(start_date_text)
        return (start + timedelta(days=day_index)).isoformat()
    except ValueError:
        return start_date_text


def build_trip_plan(request: TripRequest) -> TripPlan:
    """构造占位行程，用于打通 API 主链路。"""
    days = []
    weather_info = []

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
        overall_suggestions="当前为占位行程，下一步将接入 Agent 工作流与实时工具调用。",
        budget=budget,
    )

