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


if __name__ == "__main__":
    unittest.main()
