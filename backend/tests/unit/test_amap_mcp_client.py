"""AmapMCPClient 测试。"""

import asyncio
import unittest
from typing import Any, Dict, List

from app.core import NotFoundError
from app.integrations.mcp import AmapMCPClient


class TestAmapMCPClient(unittest.TestCase):
    """高德 MCP 客户端测试。"""

    def setUp(self) -> None:
        self.client = AmapMCPClient(
            api_key="test-key",
            command="uvx amap-mcp-server",
            mock_mode=True,
        )

    def test_search_poi_mock(self) -> None:
        result = asyncio.run(self.client.search_poi(keywords="故宫", city="北京"))
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)
        self.assertIn("name", result[0])
        self.assertIn("location", result[0])

    def test_get_weather_mock(self) -> None:
        result = asyncio.run(self.client.get_weather(city="北京"))
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)
        self.assertIn("day_weather", result[0])

    def test_call_unknown_tool(self) -> None:
        with self.assertRaises(NotFoundError):
            asyncio.run(self.client.call_tool("unknown", {}))

    def test_search_poi_via_stdio_client(self) -> None:
        class _FakeStdio:
            def __init__(self) -> None:
                self.calls: List[Dict[str, Any]] = []

            async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
                self.calls.append({"tool_name": tool_name, "arguments": arguments})
                return {
                    "pois": [
                        {
                            "id": "poi-1",
                            "name": "故宫",
                            "type": "风景名胜",
                            "address": "北京东城区景山前街4号",
                            "location": "116.397428,39.90923",
                            "tel": "010-85007421",
                        }
                    ]
                }

        fake = _FakeStdio()
        client = AmapMCPClient(
            api_key="test-key",
            command="uvx amap-mcp-server",
            mock_mode=False,
            stdio_client=fake,  # type: ignore[arg-type]
        )
        result = asyncio.run(client.search_poi(keywords="故宫", city="北京"))
        self.assertEqual(fake.calls[0]["tool_name"], "maps_text_search")
        self.assertEqual(result[0]["name"], "故宫")
        self.assertEqual(result[0]["location"]["longitude"], 116.397428)

    def test_search_poi_typecode_mapping(self) -> None:
        class _FakeStdio:
            def __init__(self) -> None:
                self.calls: List[Dict[str, Any]] = []

            async def list_tools(self) -> Any:
                return [
                    {"name": "amap_maps_text_search"},
                    {"name": "amap_maps_search_detail"},
                    {"name": "amap_maps_weather"},
                ]

            async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
                self.calls.append({"tool_name": tool_name, "arguments": arguments})
                if tool_name == "maps_text_search":
                    return {
                        "pois": [
                            {
                                "id": "poi-2",
                                "name": "国家博物馆",
                                "address": "北京市东城区东长安街16号",
                                "typecode": "140100",
                            }
                        ]
                    }
                if tool_name == "maps_search_detail":
                    return {
                        "id": "poi-2",
                        "name": "国家博物馆",
                        "address": "北京市东城区东长安街16号",
                        "location": "116.4074,39.9042",
                        "type": "科教文化服务;博物馆",
                    }
                return {}

        fake = _FakeStdio()
        client = AmapMCPClient(
            api_key="test-key",
            command="uvx amap-mcp-server",
            mock_mode=False,
            stdio_client=fake,  # type: ignore[arg-type]
        )
        with self.assertLogs("app.integrations.mcp.amap_client", level="INFO") as captured:
            result = asyncio.run(client.search_poi(keywords="博物馆", city="北京"))
        self.assertEqual(result[0]["type"], "140100")
        self.assertEqual(result[0]["location"]["longitude"], 116.4074)
        self.assertEqual(result[0]["location"]["latitude"], 39.9042)
        self.assertEqual(fake.calls[0]["tool_name"], "maps_text_search")
        self.assertEqual(fake.calls[1]["tool_name"], "maps_search_detail")
        joined = "\n".join(captured.output)
        self.assertIn("高德POI搜索", joined)
        self.assertIn("detail补全=1", joined)
        self.assertIn("MCP工具 'amap' 已展开为 3 个独立工具", joined)

    def test_search_poi_skips_detail_enrichment_when_disabled(self) -> None:
        class _FakeStdio:
            def __init__(self) -> None:
                self.calls: List[Dict[str, Any]] = []

            async def list_tools(self) -> Any:
                return [{"name": "maps_text_search"}, {"name": "maps_search_detail"}]

            async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
                self.calls.append({"tool_name": tool_name, "arguments": arguments})
                if tool_name == "maps_text_search":
                    return {
                        "pois": [
                            {
                                "id": "poi-3",
                                "name": "外滩",
                                "address": "上海市黄浦区",
                                "type": "风景名胜",
                            }
                        ]
                    }
                if tool_name == "maps_search_detail":
                    return {
                        "id": "poi-3",
                        "name": "外滩",
                        "address": "上海市黄浦区中山东一路",
                        "location": "121.490317,31.241701",
                    }
                return {}

        fake = _FakeStdio()
        client = AmapMCPClient(
            api_key="test-key",
            command="uvx amap-mcp-server",
            mock_mode=False,
            stdio_client=fake,  # type: ignore[arg-type]
        )

        result = asyncio.run(client.search_poi(keywords="外滩", city="上海", enrich_details=False))
        self.assertEqual(result[0]["location"]["longitude"], 0.0)
        self.assertEqual(result[0]["location"]["latitude"], 0.0)
        self.assertEqual([call["tool_name"] for call in fake.calls], ["maps_text_search"])

    def test_list_tools_only_queries_stdio_once_when_called_concurrently(self) -> None:
        class _FakeStdio:
            def __init__(self) -> None:
                self.list_calls = 0

            async def list_tools(self) -> Any:
                self.list_calls += 1
                await asyncio.sleep(0.02)
                return [{"name": "maps_text_search"}, {"name": "maps_weather"}]

        fake = _FakeStdio()
        client = AmapMCPClient(
            api_key="test-key",
            command="uvx amap-mcp-server",
            mock_mode=False,
            stdio_client=fake,  # type: ignore[arg-type]
        )

        async def _exercise() -> None:
            await asyncio.gather(client.list_tools(), client.list_tools(), client.list_tools())

        asyncio.run(_exercise())
        self.assertEqual(fake.list_calls, 1)

    def test_plan_route_with_nested_route_paths(self) -> None:
        class _FakeStdio:
            def __init__(self) -> None:
                self.calls: List[Dict[str, Any]] = []

            async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
                self.calls.append({"tool_name": tool_name, "arguments": arguments})
                return {
                    "route": {
                        "paths": [
                            {
                                "distance": "1064",
                                "duration": "851",
                            }
                        ]
                    }
                }

        fake = _FakeStdio()
        client = AmapMCPClient(
            api_key="test-key",
            command="uvx amap-mcp-server",
            mock_mode=False,
            stdio_client=fake,  # type: ignore[arg-type]
        )
        result = asyncio.run(
            client.plan_route(
                origin_address="天安门",
                destination_address="故宫",
                origin_city="北京",
                destination_city="北京",
                route_type="walking",
            )
        )
        self.assertEqual(result["distance"], 1064.0)
        self.assertEqual(result["duration"], 851)
        self.assertEqual(fake.calls[0]["arguments"]["origin_address"], "北京天安门")
        self.assertEqual(fake.calls[0]["arguments"]["destination_address"], "北京故宫")

    def test_plan_route_error_message_passthrough(self) -> None:
        class _FakeStdio:
            async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
                _ = tool_name, arguments
                return {"error": "Failed to geocode destination address: Geocoding failed"}

        client = AmapMCPClient(
            api_key="test-key",
            command="uvx amap-mcp-server",
            mock_mode=False,
            stdio_client=_FakeStdio(),  # type: ignore[arg-type]
        )
        result = asyncio.run(
            client.plan_route(
                origin_address="外滩",
                destination_address="东方明珠",
                origin_city="上海",
                destination_city="上海",
                route_type="walking",
            )
        )
        self.assertEqual(result["distance"], 0.0)
        self.assertEqual(result["duration"], 0)
        self.assertIn("Failed to geocode", result["description"])


if __name__ == "__main__":
    unittest.main()
