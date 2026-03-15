"""TripWorkflow 测试。"""

import asyncio
import unittest
from typing import Any, Dict, List

from app.agent.contracts import AgentRunResult, ToolTrace
from app.agent.workflows import TripWorkflow
from app.schemas import TripRequest


class _FakeRegistry:
    def __init__(self) -> None:
        self.dispatch_calls: List[Dict[str, Any]] = []

    async def dispatch(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        self.dispatch_calls.append({"tool_name": tool_name, "arguments": arguments})
        if tool_name == "search_poi":
            keyword = arguments.get("keywords", "")
            if keyword == "自然景观":
                return [
                    {"id": "nature-1", "name": "颐和园", "address": "北京", "location": "116.27,39.99"},
                    {"id": "nature-2", "name": "奥林匹克森林公园", "address": "北京", "location": "116.40,40.01"},
                ]
            if keyword == "历史文化":
                return [
                    {"id": "history-1", "name": "故宫博物院", "address": "北京", "location": "116.39,39.90"},
                    {"id": "history-2", "name": "天坛公园", "address": "北京", "location": "116.41,39.88"},
                ]
            if "酒店" in keyword or "住宿" in keyword:
                return [{"id": "hotel-1", "name": "北京酒店", "address": "北京", "location": "116.40,39.91"}]
            return [{"id": "meal-1", "name": "北京烤鸭店", "address": "北京", "location": "116.41,39.90"}]
        if tool_name == "get_weather":
            return [{"date": "2026-04-01", "day_weather": "晴", "night_weather": "多云"}]
        return {}


class _ConcurrencyTracker:
    def __init__(self) -> None:
        self.current = 0
        self.max_seen = 0

    async def hold(self, delay: float = 0.02) -> None:
        self.current += 1
        self.max_seen = max(self.max_seen, self.current)
        try:
            await asyncio.sleep(delay)
        finally:
            self.current -= 1


class _FallbackAttractionAgent:
    """始终不返回工具调用，依赖 workflow 兜底。"""

    name = "AttractionSearchAgent"

    def __init__(self, registry: _FakeRegistry) -> None:
        self.tool_registry = registry
        self.requests: List[Dict[str, str]] = []

    async def search(self, city: str, preference: str) -> AgentRunResult:
        self.requests.append({"city": city, "preference": preference})
        return AgentRunResult(content="", traces=[])


class _FallbackWeatherAgent:
    name = "WeatherQueryAgent"

    def __init__(self, registry: _FakeRegistry) -> None:
        self.tool_registry = registry
        self.cities: List[str] = []

    async def query(self, city: str) -> AgentRunResult:
        self.cities.append(city)
        return AgentRunResult(content="", traces=[])


class _FallbackHotelAgent:
    name = "HotelAgent"

    def __init__(self, registry: _FakeRegistry) -> None:
        self.tool_registry = registry
        self.requests: List[Dict[str, str]] = []

    async def search(self, city: str, accommodation: str) -> AgentRunResult:
        self.requests.append({"city": city, "accommodation": accommodation})
        return AgentRunResult(content="", traces=[])


class _FallbackMealAgent:
    name = "MealAgent"

    def __init__(self, registry: _FakeRegistry) -> None:
        self.tool_registry = registry
        self.cities: List[str] = []

    async def search(self, city: str) -> AgentRunResult:
        self.cities.append(city)
        return AgentRunResult(content="", traces=[])


class _ConcurrentAttractionAgent(_FallbackAttractionAgent):
    def __init__(self, registry: _FakeRegistry, tracker: _ConcurrencyTracker) -> None:
        super().__init__(registry)
        self.tracker = tracker

    async def search(self, city: str, preference: str) -> AgentRunResult:
        self.requests.append({"city": city, "preference": preference})
        await self.tracker.hold()
        return AgentRunResult(content="", traces=[])


class _ConcurrentWeatherAgent(_FallbackWeatherAgent):
    def __init__(self, registry: _FakeRegistry, tracker: _ConcurrencyTracker) -> None:
        super().__init__(registry)
        self.tracker = tracker

    async def query(self, city: str) -> AgentRunResult:
        self.cities.append(city)
        await self.tracker.hold()
        return AgentRunResult(content="", traces=[])


class _ConcurrentHotelAgent(_FallbackHotelAgent):
    def __init__(self, registry: _FakeRegistry, tracker: _ConcurrencyTracker) -> None:
        super().__init__(registry)
        self.tracker = tracker

    async def search(self, city: str, accommodation: str) -> AgentRunResult:
        self.requests.append({"city": city, "accommodation": accommodation})
        await self.tracker.hold()
        return AgentRunResult(content="", traces=[])


class _ConcurrentMealAgent(_FallbackMealAgent):
    def __init__(self, registry: _FakeRegistry, tracker: _ConcurrencyTracker) -> None:
        super().__init__(registry)
        self.tracker = tracker

    async def search(self, city: str) -> AgentRunResult:
        self.cities.append(city)
        await self.tracker.hold()
        return AgentRunResult(content="", traces=[])


class _PlannerAwareAgent:
    name = "PlannerAgent"

    def __init__(self, registry: _FakeRegistry) -> None:
        self.tool_registry = registry
        self.planner_contexts: List[str] = []

    async def plan(self, planner_context: str) -> AgentRunResult:
        self.planner_contexts.append(planner_context)
        return AgentRunResult(
            content=(
                '{"days":[{"day_index":0,"theme":"自然景观","description":"第1天优先安排长城。",'
                '"attraction_poi_ids":["nature-1"],"meal_names":{"breakfast":"北京烤鸭店"},'
                '"hotel_name":"北京酒店"}],"overall_suggestions":"优先满足故宫和长城偏好。"}'
            ),
            traces=[],
        )


class _ScriptedAttractionAgent(_FallbackAttractionAgent):
    async def search(self, city: str, preference: str) -> AgentRunResult:
        self.requests.append({"city": city, "preference": preference})
        return AgentRunResult(
            content="",
            traces=[
                ToolTrace(
                    agent_name=self.name,
                    tool_name="search_poi",
                    arguments={"keywords": preference, "city": city},
                    result=[{"id": "history-1", "name": "故宫博物院", "address": city, "location": "116.39,39.90"}],
                )
            ],
        )


class _ScriptedWeatherAgent(_FallbackWeatherAgent):
    async def query(self, city: str) -> AgentRunResult:
        self.cities.append(city)
        return AgentRunResult(
            content="",
            traces=[
                ToolTrace(
                    agent_name=self.name,
                    tool_name="get_weather",
                    arguments={"city": city},
                    result=[{"date": "2026-04-01", "day_weather": "晴", "night_weather": "多云"}],
                )
            ],
        )


class _ScriptedHotelAgent(_FallbackHotelAgent):
    async def search(self, city: str, accommodation: str) -> AgentRunResult:
        self.requests.append({"city": city, "accommodation": accommodation})
        return AgentRunResult(
            content="",
            traces=[
                ToolTrace(
                    agent_name=self.name,
                    tool_name="search_poi",
                    arguments={"keywords": accommodation, "city": city},
                    result=[{"id": "hotel-1", "name": "北京酒店", "address": city, "location": "116.40,39.91"}],
                )
            ],
        )


class _ScriptedMealAgent(_FallbackMealAgent):
    async def search(self, city: str) -> AgentRunResult:
        self.cities.append(city)
        return AgentRunResult(
            content="",
            traces=[
                ToolTrace(
                    agent_name=self.name,
                    tool_name="search_poi",
                    arguments={"keywords": "美食 餐厅", "city": city},
                    result=[{"id": "meal-1", "name": "北京烤鸭店", "address": city, "location": "116.41,39.90"}],
                )
            ],
        )


class _ScriptedPlannerAgent(_PlannerAwareAgent):
    async def plan(self, planner_context: str) -> AgentRunResult:
        self.planner_contexts.append(planner_context)
        return AgentRunResult(
            content=(
                '{"days":[{"day_index":0,"theme":"历史文化","description":"第1天先去故宫。",'
                '"attraction_poi_ids":["history-1"]}],"overall_suggestions":"优先历史文化。"}'
            ),
            traces=[],
        )


class TestTripWorkflow(unittest.TestCase):
    """TripWorkflow 行为测试。"""

    def setUp(self) -> None:
        self.request = TripRequest(
            city="北京",
            start_date="2026-04-01",
            end_date="2026-04-03",
            travel_days=3,
            transportation="公共交通",
            accommodation="经济型酒店",
            preferences=["自然景观", "历史文化"],
            free_text_input="希望多安排博物馆",
        )

    def test_workflow_dispatches_specialists_and_runs_final_planner(self) -> None:
        registry = _FakeRegistry()
        attraction_agent = _FallbackAttractionAgent(registry)
        weather_agent = _FallbackWeatherAgent(registry)
        hotel_agent = _FallbackHotelAgent(registry)
        meal_agent = _FallbackMealAgent(registry)
        planner_agent = _PlannerAwareAgent(registry)
        workflow = TripWorkflow(
            attraction_agent=attraction_agent,  # type: ignore[arg-type]
            weather_agent=weather_agent,  # type: ignore[arg-type]
            hotel_agent=hotel_agent,  # type: ignore[arg-type]
            meal_agent=meal_agent,  # type: ignore[arg-type]
            planner_agent=planner_agent,  # type: ignore[arg-type]
        )

        result = asyncio.run(workflow.run(self.request))
        self.assertIn("优先满足故宫和长城偏好", result.content)
        search_calls = [
            call
            for call in registry.dispatch_calls
            if call["tool_name"] == "search_poi"
            and call["arguments"]["keywords"] in {"自然景观", "历史文化"}
        ]
        self.assertEqual(
            [call["arguments"]["keywords"] for call in search_calls],
            ["自然景观", "历史文化"],
        )
        self.assertEqual(
            [item["preference"] for item in attraction_agent.requests],
            ["自然景观", "历史文化"],
        )
        self.assertEqual(weather_agent.cities, ["北京"])
        self.assertEqual(hotel_agent.requests, [{"city": "北京", "accommodation": "经济型酒店"}])
        self.assertEqual(meal_agent.cities, ["北京"])
        self.assertEqual(len(planner_agent.planner_contexts), 1)
        planner_payload = planner_agent.planner_contexts[-1]
        self.assertIn("希望多安排博物馆", planner_payload)
        self.assertIn("故宫博物院", planner_payload)
        self.assertIn("北京酒店", planner_payload)
        self.assertIn("北京烤鸭店", planner_payload)
        self.assertEqual(
            {trace.agent_name for trace in result.traces},
            {"AttractionSearchAgent", "WeatherQueryAgent", "HotelAgent", "MealAgent"},
        )

    def test_workflow_prefers_specialist_tool_traces(self) -> None:
        request = self.request.model_copy(update={"preferences": ["历史文化"]})
        registry = _FakeRegistry()
        workflow = TripWorkflow(
            attraction_agent=_ScriptedAttractionAgent(registry),  # type: ignore[arg-type]
            weather_agent=_ScriptedWeatherAgent(registry),  # type: ignore[arg-type]
            hotel_agent=_ScriptedHotelAgent(registry),  # type: ignore[arg-type]
            meal_agent=_ScriptedMealAgent(registry),  # type: ignore[arg-type]
            planner_agent=_ScriptedPlannerAgent(registry),  # type: ignore[arg-type]
        )

        result = asyncio.run(workflow.run(request))
        self.assertIn("优先历史文化", result.content)
        self.assertEqual(registry.dispatch_calls, [])
        self.assertEqual(
            [item.agent_name for item in result.traces],
            ["AttractionSearchAgent", "WeatherQueryAgent", "HotelAgent", "MealAgent"],
        )
        self.assertEqual(
            [item.tool_name for item in result.traces],
            ["search_poi", "get_weather", "search_poi", "search_poi"],
        )

    def test_workflow_logs_stage_durations(self) -> None:
        registry = _FakeRegistry()
        workflow = TripWorkflow(
            attraction_agent=_FallbackAttractionAgent(registry),  # type: ignore[arg-type]
            weather_agent=_FallbackWeatherAgent(registry),  # type: ignore[arg-type]
            hotel_agent=_FallbackHotelAgent(registry),  # type: ignore[arg-type]
            meal_agent=_FallbackMealAgent(registry),  # type: ignore[arg-type]
            planner_agent=_PlannerAwareAgent(registry),  # type: ignore[arg-type]
        )

        with self.assertLogs("app.agent.workflows.trip_workflow", level="INFO") as captured:
            asyncio.run(workflow.run(self.request))

        joined = "\n".join(captured.output)
        self.assertIn("步骤1: 搜索景点", joined)
        self.assertIn("步骤2: 查询天气", joined)
        self.assertIn("步骤3: 搜索酒店", joined)
        self.assertIn("步骤4: 搜索餐饮", joined)
        self.assertIn("步骤5: 生成行程计划", joined)
        self.assertIn("TripWorkflow 完成", joined)
        self.assertIn("耗时", joined)

    def test_workflow_runs_preplanner_stages_concurrently(self) -> None:
        registry = _FakeRegistry()
        tracker = _ConcurrencyTracker()
        workflow = TripWorkflow(
            attraction_agent=_ConcurrentAttractionAgent(registry, tracker),  # type: ignore[arg-type]
            weather_agent=_ConcurrentWeatherAgent(registry, tracker),  # type: ignore[arg-type]
            hotel_agent=_ConcurrentHotelAgent(registry, tracker),  # type: ignore[arg-type]
            meal_agent=_ConcurrentMealAgent(registry, tracker),  # type: ignore[arg-type]
            planner_agent=_PlannerAwareAgent(registry),  # type: ignore[arg-type]
        )

        asyncio.run(workflow.run(self.request))
        self.assertGreaterEqual(tracker.max_seen, 2)


if __name__ == "__main__":
    unittest.main()
