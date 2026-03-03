"""MiniAgent 运行时。"""

from __future__ import annotations

import json
from typing import Dict, List, Sequence

from app.agent.contracts import AgentRunResult, LLMClientProtocol, ToolTrace
from app.agent.parser import parse_output
from app.agent.tool_registry import ToolRegistry


class MiniAgent:
    """最小 Agent 运行时：LLM -> 解析 -> 工具 -> 迭代。"""

    def __init__(
        self,
        *,
        llm_client: LLMClientProtocol,
        tool_registry: ToolRegistry,
        max_steps: int = 6,
    ) -> None:
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.max_steps = max_steps

    async def run(self, messages: Sequence[Dict[str, str]]) -> AgentRunResult:
        history: List[Dict[str, str]] = list(messages)
        traces: List[ToolTrace] = []
        final_content = ""

        for _ in range(self.max_steps):
            raw_output = await self.llm_client.chat(history)
            content, tool_calls = parse_output(raw_output)
            if content:
                final_content = content

            if not tool_calls:
                return AgentRunResult(content=final_content, traces=traces)

            for call in tool_calls:
                result = await self.tool_registry.dispatch(call.tool_name, call.arguments)
                traces.append(
                    ToolTrace(
                        tool_name=call.tool_name,
                        arguments=call.arguments,
                        result=result,
                    )
                )
                history.append(
                    {
                        "role": "assistant",
                        "content": content or f"[TOOL_CALL:{call.tool_name}]",
                    }
                )
                history.append(
                    {
                        "role": "tool",
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )

        return AgentRunResult(content=final_content, traces=traces)

