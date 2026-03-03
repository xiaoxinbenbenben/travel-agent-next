"""TripWorkflow 测试。"""

import asyncio
import unittest
from typing import Dict, List

from app.agent.contracts import AgentRunResult
from app.agent.workflows import TripWorkflow
from app.schemas import TripRequest


class _FakeAgent:
    """用于断言输入消息的测试桩。"""

    def __init__(self) -> None:
        self.last_messages: List[Dict[str, str]] = []

    async def run(self, messages):  # type: ignore[no-untyped-def]
        self.last_messages = list(messages)
        return AgentRunResult(content="workflow-ok", traces=[])


class TestTripWorkflow(unittest.TestCase):
    """TripWorkflow 行为测试。"""

    def test_workflow_builds_messages(self) -> None:
        agent = _FakeAgent()
        workflow = TripWorkflow(agent=agent)
        request = TripRequest(
            city="北京",
            start_date="2026-04-01",
            end_date="2026-04-03",
            travel_days=3,
            transportation="公共交通",
            accommodation="经济型酒店",
            preferences=["历史文化"],
            free_text_input="希望多安排博物馆",
        )

        result = asyncio.run(workflow.run(request))
        self.assertEqual(result.content, "workflow-ok")
        self.assertEqual(len(agent.last_messages), 2)
        self.assertEqual(agent.last_messages[0]["role"], "system")
        self.assertEqual(agent.last_messages[1]["role"], "user")
        self.assertIn("目的地: 北京", agent.last_messages[1]["content"])
        self.assertIn("偏好: 历史文化", agent.last_messages[1]["content"])


if __name__ == "__main__":
    unittest.main()
