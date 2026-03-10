"""MCPStdioClient 测试。"""

import asyncio
import unittest
from dataclasses import dataclass
from typing import Any, Dict, List
from unittest.mock import patch

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
        with patch("app.integrations.mcp.stdio_client.logger.debug") as debug_log:
            with self.assertLogs("app.integrations.mcp.stdio_client", level="INFO") as captured:
                tools = asyncio.run(client.list_tools())
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "maps_text_search")
        joined = "\n".join(captured.output)
        self.assertIn("使用 Stdio 传输", joined)
        self.assertIn("连接到 MCP 服务器", joined)
        self.assertIn("连接成功", joined)
        self.assertNotIn("Processing request of type ListToolsRequest", joined)
        debug_log.assert_not_called()

    def test_call_tool_normalize_content(self) -> None:
        fake = _FakeMCPClient()
        client = MCPStdioClient(command="uvx", args=["amap-mcp-server"], client=fake)
        with patch("app.integrations.mcp.stdio_client.logger.debug") as debug_log:
            with self.assertLogs("app.integrations.mcp.stdio_client", level="INFO") as captured:
                result = asyncio.run(client.call_tool("maps_text_search", {"keywords": "故宫"}))
        self.assertEqual(fake.tool_calls[0]["tool_name"], "maps_text_search")
        self.assertEqual(result, '{"ok": true}')
        self.assertNotIn("Processing request of type CallToolRequest", "\n".join(captured.output))
        debug_log.assert_not_called()


if __name__ == "__main__":
    unittest.main()
