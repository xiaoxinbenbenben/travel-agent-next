"""TripService 测试。"""

import asyncio
import unittest
from unittest.mock import patch

from app.core import ValidationError
from app.schemas import POIInfo, RouteInfo, TripRequest, WeatherInfo
from app.services.trip_service import build_trip_plan


class _FakeMapService:
    async def search_poi(self, keywords: str, city: str, citylimit: bool = True):  # type: ignore[no-untyped-def]
        _ = citylimit
        if "美食" in keywords or "餐厅" in keywords:
            return [
                POIInfo(
                    id="meal-1",
                    name=f"{city}早餐铺",
                    type="餐饮服务",
                    address=f"{city}东城区",
                    location={"longitude": 116.38, "latitude": 39.90},
                    tel=None,
                ),
                POIInfo(
                    id="meal-2",
                    name=f"{city}午餐馆",
                    type="餐饮服务",
                    address=f"{city}西城区",
                    location={"longitude": 116.37, "latitude": 39.91},
                    tel=None,
                ),
                POIInfo(
                    id="meal-3",
                    name=f"{city}晚餐店",
                    type="餐饮服务",
                    address=f"{city}朝阳区",
                    location={"longitude": 116.43, "latitude": 39.92},
                    tel=None,
                ),
            ]
        if "酒店" in keywords or "住宿" in keywords:
            return [
                POIInfo(
                    id="hotel-1",
                    name=f"{city}中心酒店",
                    type="酒店",
                    address=f"{city}市中心",
                    location={"longitude": 116.39, "latitude": 39.91},
                    tel=None,
                )
            ]
        return [
            POIInfo(
                id="poi-1",
                name=f"{city}故宫",
                type="景点",
                address=f"{city}东城区",
                location={"longitude": 116.39, "latitude": 39.90},
                tel=None,
            ),
            POIInfo(
                id="poi-2",
                name=f"{city}天坛",
                type="景点",
                address=f"{city}崇文区",
                location={"longitude": 116.41, "latitude": 39.88},
                tel=None,
            ),
        ]

    async def get_weather(self, city: str):  # type: ignore[no-untyped-def]
        return [
            WeatherInfo(
                date="2026-04-01",
                day_weather=f"{city}晴",
                night_weather=f"{city}多云",
                day_temp=25,
                night_temp=15,
                wind_direction="东北",
                wind_power="3级",
            ),
            WeatherInfo(
                date="2026-04-02",
                day_weather=f"{city}多云",
                night_weather=f"{city}阴",
                day_temp=23,
                night_temp=14,
                wind_direction="东",
                wind_power="2级",
            ),
        ]

    async def plan_route(self, **kwargs):  # type: ignore[no-untyped-def]
        _ = kwargs
        return RouteInfo(distance=1000.0, duration=600, route_type="walking", description="示例路线")


class _FakePhotoService:
    def get_attraction_photo(self, name: str) -> str:
        return f"https://img.example.com/{name}"


class TestTripService(unittest.TestCase):
    """TripService 核心流程测试。"""

    def test_build_trip_plan_without_llm_uses_tool_fallback(self) -> None:
        request = TripRequest(
            city="北京",
            start_date="2026-04-01",
            end_date="2026-04-02",
            travel_days=2,
            transportation="公共交通",
            accommodation="经济型酒店",
            preferences=["历史文化"],
            free_text_input="希望节奏轻松",
        )

        with (
            patch("app.services.trip_service.build_llm_client", side_effect=ValidationError("no llm")),
            patch("app.services.trip_service.get_map_service", return_value=_FakeMapService()),
            patch("app.services.trip_service.get_photo_service", return_value=_FakePhotoService()),
        ):
            plan = asyncio.run(build_trip_plan(request))

        self.assertEqual(plan.city, "北京")
        self.assertEqual(len(plan.days), 2)
        self.assertGreaterEqual(len(plan.days[0].attractions), 1)
        self.assertGreaterEqual(len(plan.days[0].meals), 3)
        self.assertNotEqual(plan.days[0].meals[0].name, "第1天早餐")
        self.assertNotEqual(plan.days[0].meals[1].name, "第1天午餐")
        self.assertNotEqual(plan.days[0].meals[2].name, "第1天晚餐")
        self.assertIsNotNone(plan.days[0].hotel)
        self.assertIn("酒店", plan.days[0].hotel.name)  # type: ignore[union-attr]
        self.assertEqual(len(plan.weather_info), 2)
        self.assertIn("https://img.example.com/", plan.days[0].attractions[0].image_url or "")

        self.assertIsNotNone(plan.budget)
        budget = plan.budget
        assert budget is not None
        self.assertEqual(
            budget.total,
            budget.total_attractions
            + budget.total_hotels
            + budget.total_meals
            + budget.total_transportation,
        )


if __name__ == "__main__":
    unittest.main()
