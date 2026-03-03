"""Agent 协议对象定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol, Sequence


@dataclass(frozen=True)
class ToolCall:
    """工具调用结构。"""

    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTurnResult:
    """单轮模型输出。"""

    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)


@dataclass
class ToolTrace:
    """工具执行轨迹。"""

    tool_name: str
    arguments: Dict[str, Any]
    result: Any


@dataclass
class AgentRunResult:
    """Agent 运行结果。"""

    content: str
    traces: List[ToolTrace] = field(default_factory=list)


class LLMClientProtocol(Protocol):
    """最小 LLM 客户端协议。"""

    async def chat(self, messages: Sequence[Dict[str, str]]) -> Any:
        """返回模型输出，允许 str / dict / list。"""
        ...

