"""TripService 测试。"""

import asyncio
import unittest
from unittest.mock import patch

from app.core import ValidationError
from app.schemas import POIInfo, RouteInfo, TripRequest, WeatherInfo
from app.services.trip_service import build_trip_plan


class _FakeMapService:
    def __init__(self) -> None:
        self.search_keywords: list[str] = []
        self.route_calls = 0

    async def search_poi(self, keywords: str, city: str, citylimit: bool = True):  # type: ignore[no-untyped-def]
        _ = citylimit
        self.search_keywords.append(keywords)
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
        if keywords == "自然景观":
            return [
                POIInfo(
                    id="nature-1",
                    name=f"{city}自然景观A",
                    type="景点",
                    address=f"{city}海淀区",
                    location={"longitude": 116.30, "latitude": 39.99},
                    tel=None,
                ),
                POIInfo(
                    id="nature-2",
                    name=f"{city}自然景观B",
                    type="景点",
                    address=f"{city}朝阳区",
                    location={"longitude": 116.44, "latitude": 40.02},
                    tel=None,
                ),
                POIInfo(
                    id="nature-3",
                    name=f"{city}自然景观C",
                    type="景点",
                    address=f"{city}丰台区",
                    location={"longitude": 116.35, "latitude": 39.86},
                    tel=None,
                ),
                POIInfo(
                    id="noise-1",
                    name="天坛公园",
                    type="景点",
                    address=f"{city}东城区",
                    location={"longitude": 116.41, "latitude": 39.88},
                    tel=None,
                ),
                POIInfo(
                    id="nature-4",
                    name=f"{city}自然景观D",
                    type="景点",
                    address=f"{city}延庆区",
                    location={"longitude": 116.02, "latitude": 40.35},
                    tel=None,
                ),
                POIInfo(
                    id="nature-5",
                    name=f"{city}自然景观E",
                    type="景点",
                    address=f"{city}石景山区",
                    location={"longitude": 116.18, "latitude": 39.91},
                    tel=None,
                ),
            ]
        if keywords == "历史文化":
            return [
                POIInfo(
                    id="history-1",
                    name=f"{city}历史文化A",
                    type="景点",
                    address=f"{city}东城区",
                    location={"longitude": 116.40, "latitude": 39.91},
                    tel=None,
                ),
                POIInfo(
                    id="history-2",
                    name=f"{city}历史文化B",
                    type="景点",
                    address=f"{city}西城区",
                    location={"longitude": 116.37, "latitude": 39.91},
                    tel=None,
                ),
                POIInfo(
                    id="history-3",
                    name=f"{city}历史文化C",
                    type="景点",
                    address=f"{city}东城区",
                    location={"longitude": 116.39, "latitude": 39.90},
                    tel=None,
                ),
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
            WeatherInfo(
                date="2026-04-03",
                day_weather=f"{city}阴",
                night_weather=f"{city}小雨",
                day_temp=20,
                night_temp=12,
                wind_direction="北",
                wind_power="3级",
            ),
        ]

    async def plan_route(self, **kwargs):  # type: ignore[no-untyped-def]
        _ = kwargs
        self.route_calls += 1
        return RouteInfo(distance=1000.0, duration=600, route_type="walking", description="示例路线")


class _FakePhotoService:
    def get_attraction_photo(self, name: str) -> str:
        return f"https://img.example.com/{name}"


class _SequenceLLMClient:
    def __init__(self, outputs: list[object]) -> None:
        self.outputs = list(outputs)
        self.messages_history: list[list[dict[str, str]]] = []

    async def chat(self, messages):  # type: ignore[no-untyped-def]
        self.messages_history.append(list(messages))
        if not self.outputs:
            return ""
        return self.outputs.pop(0)


class TestTripService(unittest.TestCase):
    """TripService 核心流程测试。"""

    def test_build_trip_plan_without_llm_uses_tool_fallback(self) -> None:
        fake_map_service = _FakeMapService()
        request = TripRequest(
            city="北京",
            start_date="2026-04-01",
            end_date="2026-04-03",
            travel_days=3,
            transportation="公共交通",
            accommodation="经济型酒店",
            preferences=["自然景观", "历史文化"],
            free_text_input="希望节奏轻松",
        )

        with (
            patch("app.services.trip_service.build_llm_client", side_effect=ValidationError("no llm")),
            patch("app.services.trip_service.get_map_service", return_value=fake_map_service),
            patch("app.services.trip_service.get_photo_service", return_value=_FakePhotoService()),
        ):
            plan = asyncio.run(build_trip_plan(request))

        self.assertEqual(plan.city, "北京")
        self.assertEqual(len(plan.days), 3)
        self.assertEqual(
            fake_map_service.search_keywords[:4],
            ["自然景观", "历史文化", "经济型酒店", "美食 餐厅"],
        )
        self.assertEqual(fake_map_service.route_calls, 0)
        self.assertIn("自然景观", plan.days[0].description)
        self.assertIn("历史文化", plan.days[1].description)
        self.assertIn("自然景观", plan.days[2].description)
        self.assertGreaterEqual(len(plan.days[0].attractions), 1)
        self.assertGreaterEqual(len(plan.days[1].attractions), 1)
        self.assertGreaterEqual(len(plan.days[2].attractions), 1)
        self.assertTrue(all("自然景观" in item.name for item in plan.days[0].attractions))
        self.assertTrue(all("历史文化" in item.name for item in plan.days[1].attractions))
        self.assertTrue(all("自然景观" in item.name for item in plan.days[2].attractions))
        self.assertNotIn("天坛公园", [item.name for day in plan.days for item in day.attractions])
        self.assertTrue(
            all(
                attraction.image_url and attraction.image_url.startswith("https://img.example.com/")
                for day in plan.days
                for attraction in day.attractions
            )
        )
        self.assertGreaterEqual(len(plan.days[0].meals), 3)
        self.assertNotEqual(plan.days[0].meals[0].name, "第1天早餐")
        self.assertNotEqual(plan.days[0].meals[1].name, "第1天午餐")
        self.assertNotEqual(plan.days[0].meals[2].name, "第1天晚餐")
        self.assertIsNotNone(plan.days[0].hotel)
        self.assertIn("酒店", plan.days[0].hotel.name)  # type: ignore[union-attr]
        self.assertEqual(len(plan.weather_info), 3)
        self.assertIn("自然景观、历史文化", plan.overall_suggestions)
        self.assertNotIn("LLM 未配置", plan.overall_suggestions)

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

    def test_build_trip_plan_with_planner_agent_uses_structured_result(self) -> None:
        fake_map_service = _FakeMapService()
        fake_llm = _SequenceLLMClient(
            [
                "",
                "",
                "",
                "",
                "",
                (
                    '{"days":['
                    '{"day_index":0,"theme":"自然景观","description":"第1天先去长城。",'
                    '"attraction_poi_ids":["nature-4","nature-1"],'
                    '"meal_names":{"breakfast":"北京早餐铺","lunch":"北京午餐馆","dinner":"北京晚餐店"},'
                    '"hotel_name":"北京中心酒店"},'
                    '{"day_index":1,"theme":"历史文化","description":"第2天先去故宫。",'
                    '"attraction_poi_ids":["history-1","history-2"],'
                    '"meal_names":{"breakfast":"北京早餐铺","lunch":"北京午餐馆","dinner":"北京晚餐店"},'
                    '"hotel_name":"北京中心酒店"},'
                    '{"day_index":2,"theme":"自然景观","description":"第3天继续自然景观。",'
                    '"attraction_poi_ids":["nature-2","nature-3"],'
                    '"meal_names":{"breakfast":"北京早餐铺","lunch":"北京午餐馆","dinner":"北京晚餐店"},'
                    '"hotel_name":"北京中心酒店"}'
                    '],"overall_suggestions":"已优先满足想去长城和故宫的补充要求。"}'
                ),
            ]
        )
        request = TripRequest(
            city="北京",
            start_date="2026-04-01",
            end_date="2026-04-03",
            travel_days=3,
            transportation="公共交通",
            accommodation="经济型酒店",
            preferences=["自然景观", "历史文化"],
            free_text_input="想去故宫，长城",
        )

        with (
            patch("app.services.trip_service.build_llm_client", return_value=fake_llm),
            patch("app.services.trip_service.get_map_service", return_value=fake_map_service),
            patch("app.services.trip_service.get_photo_service", return_value=_FakePhotoService()),
            self.assertLogs("app.services.trip_service", level="INFO") as captured,
        ):
            plan = asyncio.run(build_trip_plan(request))

        self.assertEqual([item.name for item in plan.days[0].attractions], ["北京自然景观D", "北京自然景观A"])
        self.assertEqual([item.name for item in plan.days[1].attractions], ["北京历史文化A", "北京历史文化B"])
        self.assertEqual([item.name for item in plan.days[2].attractions], ["北京自然景观B", "北京自然景观C"])
        self.assertEqual(plan.days[0].description, "第1天先去长城。")
        self.assertEqual(plan.days[1].description, "第2天先去故宫。")
        self.assertEqual(plan.overall_suggestions, "已优先满足想去长城和故宫的补充要求。")
        self.assertTrue(
            all(
                attraction.image_url and attraction.image_url.startswith("https://img.example.com/")
                for day in plan.days
                for attraction in day.attractions
            )
        )
        planner_payload = "\n".join(message["content"] for message in fake_llm.messages_history[-1])
        self.assertIn("想去故宫，长城", planner_payload)
        self.assertIn("北京历史文化A", planner_payload)
        self.assertIn("北京中心酒店", planner_payload)
        joined = "\n".join(captured.output)
        self.assertIn("图片补全完成", joined)
        self.assertIn("TripPlan 构建完成", joined)

    def test_build_trip_plan_with_invalid_planner_output_falls_back_to_rules(self) -> None:
        fake_map_service = _FakeMapService()
        fake_llm = _SequenceLLMClient(["", "", "", "", "", "这不是 JSON"])
        request = TripRequest(
            city="北京",
            start_date="2026-04-01",
            end_date="2026-04-03",
            travel_days=3,
            transportation="公共交通",
            accommodation="经济型酒店",
            preferences=["自然景观", "历史文化"],
            free_text_input="想去故宫，长城",
        )

        with (
            patch("app.services.trip_service.build_llm_client", return_value=fake_llm),
            patch("app.services.trip_service.get_map_service", return_value=fake_map_service),
            patch("app.services.trip_service.get_photo_service", return_value=_FakePhotoService()),
        ):
            plan = asyncio.run(build_trip_plan(request))

        self.assertGreaterEqual(len(plan.days[0].attractions), 1)
        self.assertGreaterEqual(len(plan.days[1].attractions), 1)
        self.assertIn("自然景观、历史文化", plan.overall_suggestions)
        self.assertNotEqual(plan.overall_suggestions, "这不是 JSON")


if __name__ == "__main__":
    unittest.main()
