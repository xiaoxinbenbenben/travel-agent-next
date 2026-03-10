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
                    {"name": "颐和园", "address": "北京", "location": "116.27,39.99"},
                    {"name": "奥林匹克森林公园", "address": "北京", "location": "116.40,40.01"},
                ]
            if keyword == "历史文化":
                return [
                    {"name": "故宫博物院", "address": "北京", "location": "116.39,39.90"},
                    {"name": "天坛公园", "address": "北京", "location": "116.41,39.88"},
                ]
            return [{"name": "北京酒店", "address": "北京", "location": "116.40,39.91"}]
        if tool_name == "get_weather":
            return [{"date": "2026-04-01", "day_weather": "晴", "night_weather": "多云"}]
        if tool_name == "get_photo":
            name = str(arguments.get("name", ""))
            return {"name": name, "photo_url": f"https://img.example.com/{name}"}
        return {}


class _AlwaysEmptyAgent:
    """始终不返回工具调用，用于验证 workflow 的兜底分发。"""

    def __init__(self, registry: _FakeRegistry) -> None:
        self.tool_registry = registry
        self.messages_history: List[List[Dict[str, str]]] = []

    async def run(self, messages):  # type: ignore[no-untyped-def]
        self.messages_history.append(list(messages))
        return AgentRunResult(content="", traces=[])


class _PlannerAwareAgent(_AlwaysEmptyAgent):
    """前置阶段无工具调用，最终 planner 阶段返回结构化 JSON。"""

    async def run(self, messages):  # type: ignore[no-untyped-def]
        self.messages_history.append(list(messages))
        if len(self.messages_history) < 6:
            return AgentRunResult(content="", traces=[])
        return AgentRunResult(
            content=(
                '{"days":[{"day_index":0,"theme":"自然景观","description":"第1天优先安排长城。",'
                '"attraction_poi_ids":["nature-1"],"meal_names":{"breakfast":"北京早餐铺"},'
                '"hotel_name":"北京酒店"}],"overall_suggestions":"优先满足故宫和长城偏好。"}'
            ),
            traces=[],
        )


class _ScriptedAgent:
    """按阶段返回预设 traces。"""

    def __init__(self, registry: _FakeRegistry) -> None:
        self.tool_registry = registry
        self.count = 0

    async def run(self, messages):  # type: ignore[no-untyped-def]
        _ = messages
        self.count += 1
        if self.count == 1:
            return AgentRunResult(
                content="",
                traces=[
                    ToolTrace(
                        tool_name="search_poi",
                        arguments={"keywords": "历史文化", "city": "北京"},
                        result=[{"name": "故宫博物院", "address": "北京", "location": "116.39,39.90"}],
                    )
                ],
            )
        if self.count == 2:
            return AgentRunResult(
                content="",
                traces=[
                    ToolTrace(
                        tool_name="get_weather",
                        arguments={"city": "北京"},
                        result=[{"date": "2026-04-01", "day_weather": "晴", "night_weather": "多云"}],
                    )
                ],
            )
        if self.count == 3:
            return AgentRunResult(
                content="",
                traces=[
                    ToolTrace(
                        tool_name="search_poi",
                        arguments={"keywords": "酒店", "city": "北京"},
                        result=[{"name": "北京酒店", "address": "北京", "location": "116.40,39.91"}],
                    )
                ],
            )
        if self.count == 4:
            return AgentRunResult(
                content="",
                traces=[
                    ToolTrace(
                        tool_name="search_poi",
                        arguments={"keywords": "美食 餐厅", "city": "北京"},
                        result=[{"name": "北京烤鸭店", "address": "北京", "location": "116.41,39.90"}],
                    )
                ],
            )
        if self.count == 5:
            return AgentRunResult(
                content=(
                    '{"days":[{"day_index":0,"theme":"历史文化","description":"第1天先去故宫。",'
                    '"attraction_poi_ids":["history-1"]}],"overall_suggestions":"优先历史文化。"}'
                ),
                traces=[],
            )
        return AgentRunResult(content="", traces=[])


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

    def test_workflow_dispatches_each_preference_and_runs_final_planner(self) -> None:
        registry = _FakeRegistry()
        agent = _PlannerAwareAgent(registry)
        workflow = TripWorkflow(agent=agent)  # type: ignore[arg-type]

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
        photo_calls = [
            call["arguments"]["name"]
            for call in registry.dispatch_calls
            if call["tool_name"] == "get_photo"
        ]
        self.assertEqual(photo_calls, [])
        self.assertEqual(len(agent.messages_history), 6)
        planner_messages = agent.messages_history[-1]
        planner_payload = "\n".join(message["content"] for message in planner_messages)
        self.assertIn("希望多安排博物馆", planner_payload)
        self.assertIn("故宫博物院", planner_payload)
        self.assertIn("北京酒店", planner_payload)

    def test_workflow_prefers_agent_tool_traces(self) -> None:
        request = self.request.model_copy(update={"preferences": ["历史文化"]})
        registry = _FakeRegistry()
        agent = _ScriptedAgent(registry)
        workflow = TripWorkflow(agent=agent)  # type: ignore[arg-type]

        result = asyncio.run(workflow.run(request))
        tool_names = [item.tool_name for item in result.traces]
        self.assertIn("search_poi", tool_names)
        self.assertIn("get_weather", tool_names)
        self.assertNotIn("get_photo", tool_names)
        self.assertIn("优先历史文化", result.content)
        self.assertEqual(registry.dispatch_calls, [])

    def test_workflow_logs_stage_durations(self) -> None:
        registry = _FakeRegistry()
        agent = _PlannerAwareAgent(registry)
        workflow = TripWorkflow(agent=agent)  # type: ignore[arg-type]

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


if __name__ == "__main__":
    unittest.main()
