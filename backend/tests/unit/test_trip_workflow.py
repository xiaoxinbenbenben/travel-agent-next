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
            return [{"name": "故宫博物院", "address": "北京", "location": "116.39,39.90"}]
        if tool_name == "get_weather":
            return [{"date": "2026-04-01", "day_weather": "晴", "night_weather": "多云"}]
        if tool_name == "get_photo":
            return {"name": "故宫博物院", "photo_url": "https://img.example.com/gugong"}
        return {}


class _AlwaysEmptyAgent:
    """始终不返回工具调用，用于验证 workflow 的兜底分发。"""

    def __init__(self, registry: _FakeRegistry) -> None:
        self.tool_registry = registry
        self.messages_history: List[List[Dict[str, str]]] = []

    async def run(self, messages):  # type: ignore[no-untyped-def]
        self.messages_history.append(list(messages))
        if len(self.messages_history) >= 6:
            return AgentRunResult(content="planner-summary", traces=[])
        return AgentRunResult(content="", traces=[])


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
                content="",
                traces=[
                    ToolTrace(
                        tool_name="get_photo",
                        arguments={"name": "故宫博物院"},
                        result={"name": "故宫博物院", "photo_url": "https://img.example.com/gugong"},
                    )
                ],
            )
        return AgentRunResult(content="workflow-ok", traces=[])


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
            preferences=["历史文化"],
            free_text_input="希望多安排博物馆",
        )

    def test_workflow_fallback_dispatch_when_llm_has_no_calls(self) -> None:
        registry = _FakeRegistry()
        agent = _AlwaysEmptyAgent(registry)
        workflow = TripWorkflow(agent=agent)  # type: ignore[arg-type]

        result = asyncio.run(workflow.run(self.request))
        self.assertEqual(result.content, "planner-summary")
        self.assertGreaterEqual(len(registry.dispatch_calls), 5)
        self.assertEqual(registry.dispatch_calls[0]["tool_name"], "search_poi")
        self.assertEqual(registry.dispatch_calls[1]["tool_name"], "get_weather")
        self.assertEqual(registry.dispatch_calls[2]["tool_name"], "search_poi")
        self.assertEqual(registry.dispatch_calls[3]["tool_name"], "search_poi")

    def test_workflow_prefers_agent_tool_traces(self) -> None:
        registry = _FakeRegistry()
        agent = _ScriptedAgent(registry)
        workflow = TripWorkflow(agent=agent)  # type: ignore[arg-type]

        result = asyncio.run(workflow.run(self.request))
        self.assertEqual(result.content, "workflow-ok")
        self.assertEqual(len(registry.dispatch_calls), 0)
        tool_names = [item.tool_name for item in result.traces]
        self.assertIn("search_poi", tool_names)
        self.assertIn("get_weather", tool_names)
        self.assertIn("get_photo", tool_names)


if __name__ == "__main__":
    unittest.main()
