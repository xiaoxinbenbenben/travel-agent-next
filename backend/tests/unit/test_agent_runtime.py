"""MiniAgent 运行时测试。"""

import asyncio
import json
import unittest

from app.agent.runtime import MiniAgent
from app.agent.tool_registry import ToolRegistry


class FakeLLM:
    """可控的测试模型。"""

    def __init__(self) -> None:
        self._count = 0
        self.calls = []

    async def chat(self, messages):  # type: ignore[no-untyped-def]
        self.calls.append([{"role": item["role"], "content": item["content"]} for item in messages])
        self._count += 1
        if self._count == 1:
            return '[{"tool_name":"echo","arguments":{"text":"hello"}}]'
        return "最终建议：行程可执行。"


class TestAgentRuntime(unittest.TestCase):
    """Agent 运行时测试。"""

    def test_runtime_executes_tool_and_returns_final_content(self) -> None:
        registry = ToolRegistry()
        registry.register("echo", lambda payload: {"echo": payload["text"]})
        fake_llm = FakeLLM()
        agent = MiniAgent(
            name="EchoAgent",
            llm_client=fake_llm,
            tool_registry=registry,
            max_steps=3,
        )

        result = asyncio.run(agent.run([{"role": "user", "content": "请给出建议"}]))
        self.assertEqual(result.content, "最终建议：行程可执行。")
        self.assertEqual(len(result.traces), 1)
        self.assertEqual(result.traces[0].agent_name, "EchoAgent")
        self.assertEqual(result.traces[0].tool_name, "echo")
        self.assertEqual(result.traces[0].result["echo"], "hello")

        self.assertEqual(len(fake_llm.calls), 2)
        second_round_messages = fake_llm.calls[1]
        self.assertTrue(all(item["role"] != "tool" for item in second_round_messages))

        assistant_message = second_round_messages[-2]
        self.assertEqual(assistant_message["role"], "assistant")
        assistant_payload = json.loads(assistant_message["content"])
        self.assertEqual(assistant_payload["tool_name"], "echo")
        self.assertEqual(assistant_payload["arguments"], {"text": "hello"})

        result_message = second_round_messages[-1]
        self.assertEqual(result_message["role"], "user")
        self.assertTrue(result_message["content"].startswith("[TOOL_RESULT:echo] "))
        result_payload = json.loads(result_message["content"].split("] ", 1)[1])
        self.assertEqual(result_payload, {"echo": "hello"})


if __name__ == "__main__":
    unittest.main()
