"""高德 MCP 客户端封装（基于通用 stdio 客户端）。"""

from __future__ import annotations

import json
import re
import shlex
from datetime import date
from functools import lru_cache
from typing import Any, Dict, List, Optional

from app.core import NotFoundError, ValidationError, get_settings
from app.integrations.mcp.stdio_client import MCPStdioClient

_JSON_BLOCK_PATTERN = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)


class AmapMCPClient:
    """高德工具语义封装，底层通过 MCP stdio 调用。"""

    def __init__(
        self,
        *,
        api_key: str,
        command: str,
        mock_mode: bool = True,
        stdio_client: MCPStdioClient | None = None,
    ) -> None:
        if not api_key:
            raise ValidationError("AMAP_API_KEY 未配置，无法创建 AmapMCPClient")

        self.api_key = api_key
        self.command = command
        # mock 模式用于离线开发；关闭后走真实 MCP stdio 调用。
        self.mock_mode = mock_mode

        if stdio_client is not None:
            self._stdio_client = stdio_client
        else:
            parts = shlex.split(command)
            if not parts:
                raise ValidationError("AMAP_MCP_COMMAND 无效")
            self._stdio_client = MCPStdioClient(
                command=parts[0],
                args=parts[1:],
                # 对齐旧项目：高德 MCP 进程读取 AMAP_MAPS_API_KEY。
                env={"AMAP_MAPS_API_KEY": api_key},
                timeout_seconds=30,
            )

    async def list_tools(self) -> List[str]:
        if self.mock_mode:
            return ["search_poi", "get_weather", "plan_route", "get_poi_detail"]

        tools = await self._stdio_client.list_tools()
        return [item.get("name", "") for item in tools if item.get("name")]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        if tool_name == "search_poi":
            return await self.search_poi(
                keywords=str(arguments.get("keywords", "")),
                city=str(arguments.get("city", "")),
                citylimit=bool(arguments.get("citylimit", True)),
            )
        if tool_name == "get_weather":
            return await self.get_weather(city=str(arguments.get("city", "")))
        if tool_name == "plan_route":
            return await self.plan_route(
                origin_address=str(arguments.get("origin_address", "")),
                destination_address=str(arguments.get("destination_address", "")),
                origin_city=arguments.get("origin_city"),
                destination_city=arguments.get("destination_city"),
                route_type=str(arguments.get("route_type", "walking")),
            )
        if tool_name == "get_poi_detail":
            return await self.get_poi_detail(poi_id=str(arguments.get("poi_id", "")))

        raise NotFoundError(f"不支持的工具: {tool_name}", details={"tool_name": tool_name})

    async def search_poi(self, *, keywords: str, city: str, citylimit: bool = True) -> List[Dict[str, Any]]:
        if self.mock_mode:
            return [
                {
                    "id": f"{city}-{keywords}-001",
                    "name": f"{keywords}（示例）",
                    "type": "景点",
                    "address": f"{city}核心区域",
                    "location": {"longitude": 116.397428, "latitude": 39.90923},
                    "tel": None,
                }
            ]

        # 工具名映射到 amap-mcp-server 的原生工具名。
        raw = await self._stdio_client.call_tool(
            "maps_text_search",
            {
                "keywords": keywords,
                "city": city,
                "citylimit": str(citylimit).lower(),
            },
        )
        parsed = self._coerce_json(raw)
        items = self._extract_poi_items(parsed)
        normalized = [self._normalize_poi_item(item) for item in items]

        # maps_text_search 常不返回 location，补一次 detail 查询拿完整坐标。
        for poi in normalized:
            poi_id = str(poi.get("id", "")).strip()
            if not poi_id or not self._is_empty_location(poi.get("location")):
                continue
            try:
                detail = await self.get_poi_detail(poi_id=poi_id)
            except Exception:
                continue
            if not isinstance(detail, dict):
                continue

            if detail.get("location") is not None:
                poi["location"] = self._parse_location(detail.get("location"))
            if not poi.get("address") and detail.get("address"):
                poi["address"] = str(detail.get("address", ""))
            if not poi.get("type") and detail.get("type"):
                poi["type"] = str(detail.get("type", ""))
            if not poi.get("tel") and detail.get("tel"):
                poi["tel"] = str(detail.get("tel", ""))

        return normalized

    async def get_weather(self, *, city: str) -> List[Dict[str, Any]]:
        if self.mock_mode:
            today = date.today().isoformat()
            return [
                {
                    "date": today,
                    "day_weather": f"{city}晴",
                    "night_weather": f"{city}多云",
                    "day_temp": 26,
                    "night_temp": 18,
                    "wind_direction": "东北",
                    "wind_power": "3级",
                }
            ]

        raw = await self._stdio_client.call_tool("maps_weather", {"city": city})
        parsed = self._coerce_json(raw)
        return self._normalize_weather_items(parsed)

    async def plan_route(
        self,
        *,
        origin_address: str,
        destination_address: str,
        origin_city: str | None = None,
        destination_city: str | None = None,
        route_type: str = "walking",
    ) -> Dict[str, Any]:
        if self.mock_mode:
            _ = origin_city, destination_city
            return {
                "distance": 3200.0,
                "duration": 2400,
                "route_type": route_type,
                "description": f"从“{origin_address}”到“{destination_address}”的{route_type}路线（示例）",
            }

        tool_map = {
            "walking": "maps_direction_walking_by_address",
            "driving": "maps_direction_driving_by_address",
            "transit": "maps_direction_transit_integrated_by_address",
        }
        tool_name = tool_map.get(route_type, "maps_direction_walking_by_address")
        origin_for_query = self._augment_address_with_city(origin_address, origin_city)
        destination_for_query = self._augment_address_with_city(destination_address, destination_city)
        # 路由工具参数名对齐旧接口字段，便于 API 层透传。
        raw = await self._stdio_client.call_tool(
            tool_name,
            {
                "origin_address": origin_for_query,
                "destination_address": destination_for_query,
                "origin_city": origin_city,
                "destination_city": destination_city,
            },
        )
        parsed = self._coerce_json(raw)
        return self._normalize_route(parsed, route_type, origin_address, destination_address)

    async def get_poi_detail(self, *, poi_id: str) -> Dict[str, Any]:
        if self.mock_mode:
            return {
                "id": poi_id,
                "name": f"POI-{poi_id}",
                "address": "示例地址",
                "location": "116.397428,39.90923",
            }

        raw = await self._stdio_client.call_tool("maps_search_detail", {"id": poi_id})
        parsed = self._coerce_json(raw)

        if isinstance(parsed, dict):
            if "pois" in parsed and isinstance(parsed["pois"], list) and parsed["pois"]:
                first = parsed["pois"][0]
                if isinstance(first, dict):
                    return {
                        "id": str(first.get("id", poi_id)),
                        "name": str(first.get("name", "")),
                        "address": str(first.get("address", "")),
                        "location": str(first.get("location", "")),
                        "tel": str(first.get("tel", "")),
                        "type": str(first.get("type", "")),
                    }
            return parsed

        return {"id": poi_id, "raw": parsed}

    @staticmethod
    def _coerce_json(raw: Any) -> Any:
        if isinstance(raw, (dict, list)):
            return raw

        if not isinstance(raw, str):
            return raw

        text = raw.strip()
        if not text:
            return {}

        # 支持 ```json ... ``` 输出
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3:
                text = "\n".join(lines[1:-1]).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 兼容模型或 MCP 结果前后带解释文本的场景，提取首个 JSON 片段。
        match = _JSON_BLOCK_PATTERN.search(text)
        if match:
            candidate = match.group(1)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                return {"raw": text}

        return {"raw": text}

    @staticmethod
    def _parse_location(location: Any) -> Dict[str, float]:
        if isinstance(location, dict):
            return {
                "longitude": AmapMCPClient._to_float(
                    location.get("longitude", location.get("lon", 0.0)),
                    0.0,
                ),
                "latitude": AmapMCPClient._to_float(
                    location.get("latitude", location.get("lat", 0.0)),
                    0.0,
                ),
            }
        if isinstance(location, str) and "," in location:
            lon, lat = location.split(",", 1)
            return {
                "longitude": AmapMCPClient._to_float(lon, 0.0),
                "latitude": AmapMCPClient._to_float(lat, 0.0),
            }
        return {"longitude": 0.0, "latitude": 0.0}

    @staticmethod
    def _extract_poi_items(parsed: Any) -> List[Dict[str, Any]]:
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        if isinstance(parsed, dict):
            if isinstance(parsed.get("pois"), list):
                return [item for item in parsed["pois"] if isinstance(item, dict)]
            if isinstance(parsed.get("data"), list):
                return [item for item in parsed["data"] if isinstance(item, dict)]
        return []

    def _normalize_poi_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        location = item.get("location")
        if location is None and item.get("lon") is not None and item.get("lat") is not None:
            location = {"lon": item.get("lon"), "lat": item.get("lat")}

        poi_type = item.get("type", item.get("typecode", ""))
        tel = item.get("tel", item.get("phone"))

        return {
            "id": str(item.get("id", item.get("poi_id", ""))),
            "name": str(item.get("name", "")),
            "type": str(poi_type),
            "address": str(item.get("address", item.get("formatted_address", ""))),
            "location": self._parse_location(location),
            "tel": str(tel) if tel else None,
        }

    @staticmethod
    def _is_empty_location(location: Any) -> bool:
        parsed = AmapMCPClient._parse_location(location)
        return parsed["longitude"] == 0.0 and parsed["latitude"] == 0.0

    @staticmethod
    def _augment_address_with_city(address: str, city: str | None) -> str:
        base = address.strip()
        if not base:
            return address
        if not city:
            return base

        city_text = city.strip()
        if not city_text:
            return base
        if city_text in base:
            return base

        if city_text.endswith(("市", "区", "县", "省")):
            short_city = city_text[:-1]
            if short_city and short_city in base:
                return base

        return f"{city_text}{base}"

    def _normalize_weather_items(self, parsed: Any) -> List[Dict[str, Any]]:
        if isinstance(parsed, dict) and isinstance(parsed.get("forecasts"), list) and parsed["forecasts"]:
            casts = parsed["forecasts"]
            result: List[Dict[str, Any]] = []
            for cast in casts:
                if not isinstance(cast, dict):
                    continue
                result.append(
                    {
                        "date": str(cast.get("date", "")),
                        "day_weather": str(cast.get("dayweather", "")),
                        "night_weather": str(cast.get("nightweather", "")),
                        "day_temp": cast.get("daytemp", 0),
                        "night_temp": cast.get("nighttemp", 0),
                        "wind_direction": str(cast.get("daywind", "")),
                        "wind_power": str(cast.get("daypower", "")),
                    }
                )
            return result

        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        if isinstance(parsed, dict) and isinstance(parsed.get("data"), list):
            return [item for item in parsed["data"] if isinstance(item, dict)]
        return []

    @staticmethod
    def _normalize_route(
        parsed: Any,
        route_type: str,
        origin_address: str,
        destination_address: str,
    ) -> Dict[str, Any]:
        metrics = AmapMCPClient._extract_route_metrics(parsed)
        route_error = AmapMCPClient._extract_route_error(parsed)
        if metrics is not None:
            distance, duration = metrics
            description = ""
            if isinstance(parsed, dict):
                description = str(parsed.get("description", ""))
                route = parsed.get("route")
                if not description and isinstance(route, dict):
                    description = str(route.get("description", ""))

            return {
                "distance": distance,
                "duration": duration,
                "route_type": route_type,
                "description": description or f"{origin_address} -> {destination_address}",
            }

        return {
            "distance": 0.0,
            "duration": 0,
            "route_type": route_type,
            "description": (
                f"路线规划失败: {route_error}"
                if route_error
                else f"路线结果待解析: {origin_address} -> {destination_address}"
            ),
        }

    @staticmethod
    def _extract_route_metrics(parsed: Any) -> tuple[float, int] | None:
        if not isinstance(parsed, dict):
            return None

        # 兼容扁平结构：{"distance": "...", "duration": "..."}
        if "distance" in parsed or "duration" in parsed:
            distance = AmapMCPClient._to_float(parsed.get("distance", 0.0), 0.0)
            duration = AmapMCPClient._to_int(parsed.get("duration", 0), 0)
            if distance > 0 or duration > 0:
                return distance, duration

        route = parsed.get("route")
        if not isinstance(route, dict):
            return None

        # amap-mcp-server 常见格式：route.paths[0].distance / duration
        paths = route.get("paths")
        if isinstance(paths, list):
            for path in paths:
                if not isinstance(path, dict):
                    continue
                distance = AmapMCPClient._to_float(
                    path.get("distance", route.get("distance", 0.0)),
                    0.0,
                )
                duration = AmapMCPClient._to_int(
                    path.get("duration", route.get("duration", 0)),
                    0,
                )
                if distance > 0 or duration > 0:
                    return distance, duration

        # 公交场景：route.distance + route.transits[0].duration（或 transits[0].distance）
        transits = route.get("transits")
        if isinstance(transits, list):
            for transit in transits:
                if not isinstance(transit, dict):
                    continue
                distance = AmapMCPClient._to_float(
                    transit.get("distance", route.get("distance", 0.0)),
                    0.0,
                )
                duration = AmapMCPClient._to_int(
                    transit.get("duration", route.get("duration", 0)),
                    0,
                )
                if distance > 0 or duration > 0:
                    return distance, duration

        distance = AmapMCPClient._to_float(route.get("distance", 0.0), 0.0)
        duration = AmapMCPClient._to_int(route.get("duration", 0), 0)
        if distance > 0 or duration > 0:
            return distance, duration

        return None

    @staticmethod
    def _extract_route_error(parsed: Any) -> str:
        if isinstance(parsed, dict):
            for key in ("error", "message", "msg"):
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return ""

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_int(value: Any, default: int = 0) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


@lru_cache()
def get_amap_mcp_client() -> AmapMCPClient:
    settings = get_settings()
    # 单例复用：多个服务/Agent 共用同一客户端配置与连接策略。
    return AmapMCPClient(
        api_key=settings.amap_api_key,
        command=settings.amap_mcp_command,
        mock_mode=settings.amap_mcp_mock,
    )
