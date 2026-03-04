"""模型输出解析器：结构化 JSON + 旧 TOOL_CALL 兜底。"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple

from app.agent.contracts import ToolCall

_TOOL_CALL_PATTERN = re.compile(r"\[TOOL_CALL:(?P<body>[^\]]+)\]")
_LEGACY_TOOL_MAP = {
    "amap_maps_text_search": "search_poi",
    "maps_text_search": "search_poi",
    "amap_maps_weather": "get_weather",
    "maps_weather": "get_weather",
    "amap_maps_search_detail": "get_poi_detail",
    "maps_search_detail": "get_poi_detail",
    "amap_maps_direction_walking_by_address": "plan_route",
    "maps_direction_walking_by_address": "plan_route",
    "amap_maps_direction_driving_by_address": "plan_route",
    "maps_direction_driving_by_address": "plan_route",
    "amap_maps_direction_transit_integrated_by_address": "plan_route",
    "maps_direction_transit_integrated_by_address": "plan_route",
}
_LEGACY_ROUTE_TYPE_MAP = {
    "amap_maps_direction_walking_by_address": "walking",
    "maps_direction_walking_by_address": "walking",
    "amap_maps_direction_driving_by_address": "driving",
    "maps_direction_driving_by_address": "driving",
    "amap_maps_direction_transit_integrated_by_address": "transit",
    "maps_direction_transit_integrated_by_address": "transit",
}


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
        body = match.group("body").strip()
        if not body:
            continue

        name, arguments = _parse_legacy_body(body)
        if not name:
            continue

        normalized_name = _LEGACY_TOOL_MAP.get(name, name)
        normalized_args = _normalize_legacy_arguments(name, normalized_name, arguments)
        calls.append(ToolCall(tool_name=normalized_name, arguments=normalized_args))
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


def _parse_legacy_body(body: str) -> Tuple[str, Dict[str, Any]]:
    # 兼容旧式：tool{json}
    if "{" in body and body.endswith("}"):
        brace_index = body.find("{")
        if brace_index > 0:
            name = body[:brace_index].rstrip(":").strip()
            json_text = body[brace_index:].strip()
            if name:
                try:
                    loaded = json.loads(json_text)
                    if isinstance(loaded, dict):
                        return name, loaded
                except json.JSONDecodeError:
                    return name, {}

    # 兼容旧式：tool:params
    if ":" in body:
        name, params_text = body.split(":", 1)
        return name.strip(), _parse_legacy_params(params_text.strip())

    return body.strip(), {}


def _parse_legacy_params(params_text: str) -> Dict[str, Any]:
    if not params_text:
        return {}

    if params_text.startswith("{"):
        try:
            parsed = json.loads(params_text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}

    if "=" in params_text:
        parsed: Dict[str, Any] = {}
        for chunk in params_text.split(","):
            piece = chunk.strip()
            if not piece or "=" not in piece:
                continue
            key, value = piece.split("=", 1)
            parsed[key.strip()] = _coerce_scalar(value.strip())
        return parsed

    return {"input": params_text}


def _coerce_scalar(raw: str) -> Any:
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"

    if re.fullmatch(r"-?\d+", raw):
        try:
            return int(raw)
        except ValueError:
            return raw

    if re.fullmatch(r"-?\d+\.\d+", raw):
        try:
            return float(raw)
        except ValueError:
            return raw

    return raw


def _normalize_legacy_arguments(
    original_name: str,
    normalized_name: str,
    arguments: Dict[str, Any],
) -> Dict[str, Any]:
    payload = dict(arguments)

    if normalized_name == "search_poi":
        if "keywords" not in payload and "query" in payload:
            payload["keywords"] = payload["query"]
        if "keywords" not in payload and "input" in payload:
            payload["keywords"] = payload["input"]
        if "citylimit" not in payload:
            payload["citylimit"] = True
    elif normalized_name == "get_weather":
        if "city" not in payload and "input" in payload:
            payload["city"] = payload["input"]
    elif normalized_name == "get_poi_detail":
        if "poi_id" not in payload and "id" in payload:
            payload["poi_id"] = payload["id"]
        if "poi_id" not in payload and "input" in payload:
            payload["poi_id"] = payload["input"]
    elif normalized_name == "get_photo":
        if "name" not in payload and "input" in payload:
            payload["name"] = payload["input"]
    elif normalized_name == "plan_route":
        if "route_type" not in payload:
            route_type = _LEGACY_ROUTE_TYPE_MAP.get(original_name)
            if route_type:
                payload["route_type"] = route_type

    payload.pop("input", None)
    return payload
