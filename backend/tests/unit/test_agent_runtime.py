"""MiniAgent 运行时测试。"""

import asyncio
import unittest

from app.agent.runtime import MiniAgent
from app.agent.tool_registry import ToolRegistry


class FakeLLM:
    """可控的测试模型。"""

    def __init__(self) -> None:
        self._count = 0

    async def chat(self, messages):  # type: ignore[no-untyped-def]
        _ = messages
        self._count += 1
        if self._count == 1:
            return '[{"tool_name":"echo","arguments":{"text":"hello"}}]'
        return "最终建议：行程可执行。"


class TestAgentRuntime(unittest.TestCase):
    """Agent 运行时测试。"""

    def test_runtime_executes_tool_and_returns_final_content(self) -> None:
        registry = ToolRegistry()
        registry.register("echo", lambda payload: {"echo": payload["text"]})
        agent = MiniAgent(llm_client=FakeLLM(), tool_registry=registry, max_steps=3)

        result = asyncio.run(agent.run([{"role": "user", "content": "请给出建议"}]))
        self.assertEqual(result.content, "最终建议：行程可执行。")
        self.assertEqual(len(result.traces), 1)
        self.assertEqual(result.traces[0].tool_name, "echo")
        self.assertEqual(result.traces[0].result["echo"], "hello")


if __name__ == "__main__":
    unittest.main()
