"""LLM 客户端测试。"""

import asyncio
import unittest
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, List

from app.core import ExternalServiceError
from app.integrations.llm.client import OpenAICompatibleLLMClient


@dataclass
class _FakeFunction:
    name: str
    arguments: str


@dataclass
class _FakeToolCall:
    function: _FakeFunction


@dataclass
class _FakeMessage:
    content: Any
    tool_calls: List[_FakeToolCall] | None = None


@dataclass
class _FakeChoice:
    message: _FakeMessage


@dataclass
class _FakeResponse:
    choices: List[_FakeChoice]


class _FakeCompletions:
    def __init__(self, response: _FakeResponse | None = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error

    async def create(self, **_: Any) -> _FakeResponse:
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


class _FakeOpenAIClient:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.chat = SimpleNamespace(completions=completions)


class TestOpenAICompatibleLLMClient(unittest.TestCase):
    """LLM 客户端行为测试。"""

    def test_chat_returns_plain_text(self) -> None:
        response = _FakeResponse(choices=[_FakeChoice(message=_FakeMessage(content="hello"))])
        fake_client = _FakeOpenAIClient(_FakeCompletions(response=response))
        llm_client = OpenAICompatibleLLMClient(
            api_key="test-key",
            base_url="https://example.com/v1",
            model="test-model",
            timeout_seconds=30,
            client=fake_client,
        )

        result = asyncio.run(llm_client.chat([{"role": "user", "content": "hi"}]))
        self.assertEqual(result, "hello")

    def test_chat_returns_structured_tool_calls(self) -> None:
        tool_calls = [
            _FakeToolCall(function=_FakeFunction(name="search_poi", arguments='{"city":"北京"}')),
        ]
        response = _FakeResponse(
            choices=[_FakeChoice(message=_FakeMessage(content="", tool_calls=tool_calls))]
        )
        fake_client = _FakeOpenAIClient(_FakeCompletions(response=response))
        llm_client = OpenAICompatibleLLMClient(
            api_key="test-key",
            base_url="https://example.com/v1",
            model="test-model",
            timeout_seconds=30,
            client=fake_client,
        )

        result = asyncio.run(llm_client.chat([{"role": "user", "content": "hi"}]))
        self.assertEqual(
            result,
            [{"tool_name": "search_poi", "arguments": {"city": "北京"}}],
        )

    def test_chat_raises_external_service_error(self) -> None:
        fake_client = _FakeOpenAIClient(_FakeCompletions(error=RuntimeError("boom")))
        llm_client = OpenAICompatibleLLMClient(
            api_key="test-key",
            base_url="https://example.com/v1",
            model="test-model",
            timeout_seconds=30,
            client=fake_client,
        )

        with self.assertRaises(ExternalServiceError):
            asyncio.run(llm_client.chat([{"role": "user", "content": "hi"}]))


if __name__ == "__main__":
    unittest.main()
