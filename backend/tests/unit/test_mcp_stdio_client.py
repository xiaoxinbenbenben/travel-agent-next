"""MCPStdioClient 测试。"""

import asyncio
import unittest
from dataclasses import dataclass
from typing import Any, Dict, List

from app.integrations.mcp import MCPStdioClient


@dataclass
class _FakeTool:
    name: str
    description: str = ""
    inputSchema: Dict[str, Any] | None = None


@dataclass
class _FakeTextContent:
    text: str


@dataclass
class _FakeToolResult:
    content: List[Any]


class _FakeMCPClient:
    def __init__(self) -> None:
        self.tool_calls: List[Dict[str, Any]] = []

    async def list_tools(self) -> Any:
        return type("Result", (), {"tools": [_FakeTool(name="maps_text_search", description="搜索")]})()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        self.tool_calls.append({"tool_name": tool_name, "arguments": arguments})
        return _FakeToolResult(content=[_FakeTextContent(text='{"ok": true}')])


class TestMCPStdioClient(unittest.TestCase):
    """通用 stdio 客户端行为测试。"""

    def test_list_tools_normalize(self) -> None:
        client = MCPStdioClient(command="uvx", args=["amap-mcp-server"], client=_FakeMCPClient())
        tools = asyncio.run(client.list_tools())
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "maps_text_search")

    def test_call_tool_normalize_content(self) -> None:
        fake = _FakeMCPClient()
        client = MCPStdioClient(command="uvx", args=["amap-mcp-server"], client=fake)
        result = asyncio.run(client.call_tool("maps_text_search", {"keywords": "故宫"}))
        self.assertEqual(fake.tool_calls[0]["tool_name"], "maps_text_search")
        self.assertEqual(result, '{"ok": true}')


if __name__ == "__main__":
    unittest.main()
