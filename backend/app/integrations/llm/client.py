"""OpenAI-compatible LLM 客户端封装。"""

from __future__ import annotations

import json
from typing import Any, Dict, Sequence

from openai import AsyncOpenAI

from app.core import ExternalServiceError, ValidationError, get_settings


class OpenAICompatibleLLMClient:
    """OpenAI 兼容协议客户端。"""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: int = 60,
        client: Any | None = None,
    ) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._client = client or AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
        )

    @staticmethod
    def _parse_tool_calls(tool_calls: Any) -> list[dict[str, Any]]:
        if not tool_calls:
            return []

        parsed: list[dict[str, Any]] = []
        for tool_call in tool_calls:
            function = getattr(tool_call, "function", None)
            name = getattr(function, "name", "") if function is not None else ""
            arguments_text = getattr(function, "arguments", "{}") if function is not None else "{}"

            if not isinstance(name, str) or not name.strip():
                continue

            arguments: Dict[str, Any] = {}
            if isinstance(arguments_text, str) and arguments_text.strip():
                try:
                    loaded = json.loads(arguments_text)
                    if isinstance(loaded, dict):
                        arguments = loaded
                except json.JSONDecodeError:
                    arguments = {}

            parsed.append({"tool_name": name.strip(), "arguments": arguments})
        return parsed

    @staticmethod
    def _extract_content(message: Any) -> str:
        content = getattr(message, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts: list[str] = []
            for part in content:
                if isinstance(part, str):
                    texts.append(part)
                elif isinstance(part, dict) and isinstance(part.get("text"), str):
                    texts.append(part["text"])
                else:
                    text_value = getattr(part, "text", None)
                    if isinstance(text_value, str):
                        texts.append(text_value)
            return "".join(texts)
        return str(content or "")

    async def chat(self, messages: Sequence[Dict[str, str]]) -> Any:
        """调用 LLM 并返回文本或结构化工具调用。"""
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=list(messages),
            )
        except Exception as exc:
            raise ExternalServiceError(
                "LLM 调用失败",
                details={"provider": "openai-compatible", "error": str(exc)},
            ) from exc

        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""

        message = getattr(choices[0], "message", None)
        if message is None:
            return ""

        tool_calls = self._parse_tool_calls(getattr(message, "tool_calls", None))
        if tool_calls:
            return tool_calls

        return self._extract_content(message)


def build_llm_client() -> OpenAICompatibleLLMClient:
    """根据全局配置创建 LLM 客户端。"""
    settings = get_settings()
    if not settings.llm_api_key:
        raise ValidationError("LLM_API_KEY 未配置，无法创建 LLM 客户端")

    return OpenAICompatibleLLMClient(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model_id,
        timeout_seconds=settings.llm_timeout,
    )

