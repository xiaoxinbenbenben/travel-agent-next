"""模型输出解析器：结构化 JSON + 旧 TOOL_CALL 兜底。"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple

from app.agent.contracts import ToolCall

_TOOL_CALL_PATTERN = re.compile(
    r"\[TOOL_CALL:(?P<name>[a-zA-Z0-9_\-]+)(?P<args>\{.*?\})?\]",
    re.DOTALL,
)


def _as_tool_call(payload: Dict[str, Any]) -> ToolCall | None:
    tool_name = payload.get("tool_name") or payload.get("name")
    if not isinstance(tool_name, str) or not tool_name.strip():
        return None

    arguments = payload.get("arguments", {})
    if not isinstance(arguments, dict):
        arguments = {}
    return ToolCall(tool_name=tool_name.strip(), arguments=arguments)


def _parse_json_calls(raw: str) -> List[ToolCall]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if isinstance(parsed, dict):
        call = _as_tool_call(parsed)
        return [call] if call else []

    if isinstance(parsed, list):
        calls: List[ToolCall] = []
        for item in parsed:
            if isinstance(item, dict):
                call = _as_tool_call(item)
                if call:
                    calls.append(call)
        return calls

    return []


def _parse_legacy_tool_calls(raw: str) -> List[ToolCall]:
    calls: List[ToolCall] = []
    for match in _TOOL_CALL_PATTERN.finditer(raw):
        name = match.group("name").strip()
        args_text = (match.group("args") or "").strip()
        arguments: Dict[str, Any] = {}

        if args_text:
            try:
                parsed_args = json.loads(args_text)
                if isinstance(parsed_args, dict):
                    arguments = parsed_args
            except json.JSONDecodeError:
                arguments = {}

        calls.append(ToolCall(tool_name=name, arguments=arguments))
    return calls


def parse_output(raw_output: Any) -> Tuple[str, List[ToolCall]]:
    """解析模型输出，返回正文与工具调用。"""
    if isinstance(raw_output, dict):
        call = _as_tool_call(raw_output)
        if call:
            return "", [call]
        return json.dumps(raw_output, ensure_ascii=False), []

    if isinstance(raw_output, list):
        calls: List[ToolCall] = []
        for item in raw_output:
            if isinstance(item, dict):
                call = _as_tool_call(item)
                if call:
                    calls.append(call)
        if calls:
            return "", calls
        return json.dumps(raw_output, ensure_ascii=False), []

    if not isinstance(raw_output, str):
        return str(raw_output), []

    text = raw_output.strip()
    if not text:
        return "", []

    json_calls = _parse_json_calls(text)
    if json_calls:
        return "", json_calls

    legacy_calls = _parse_legacy_tool_calls(text)
    if legacy_calls:
        return text, legacy_calls

    return text, []

