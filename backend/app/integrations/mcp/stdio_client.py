"""通用 MCP stdio 客户端。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from app.core import ExternalServiceError

logger = logging.getLogger(__name__)


class MCPStdioClient:
    """基于 fastmcp.Client 的通用 stdio 封装。"""

    def __init__(
        self,
        *,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 30,
        client: Any | None = None,
    ) -> None:
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.timeout_seconds = timeout_seconds

        self._injected_client = client
        self._client: Any | None = None
        self._context: Any | None = None

    async def connect(self) -> None:
        # 连接复用：同一个 client 在进程内只建立一次 stdio 会话。
        if self._client is not None:
            return

        command_text = " ".join([self.command, *self.args]).strip()
        logger.info("📝 使用 Stdio 传输 (命令): %s", command_text)
        logger.info("🔗 连接到 MCP 服务器...")

        if self._injected_client is not None:
            # 测试场景可注入 fake client，避免真实拉起子进程。
            self._client = self._injected_client
            if hasattr(self._client, "__aenter__"):
                self._context = self._client
                self._client = await self._context.__aenter__()
            logger.info("✅ 连接成功！")
            return

        # fastmcp 3.x 使用 StdioTransport 描述 stdio 子进程启动方式。
        transport = StdioTransport(
            command=self.command,
            args=self.args,
            env=self.env if self.env else None,
        )
        self._context = Client(transport, timeout=self.timeout_seconds)
        self._client = await self._context.__aenter__()
        logger.info("✅ 连接成功！")

    async def close(self) -> None:
        if self._context is not None:
            await self._context.__aexit__(None, None, None)
            logger.info("🔌 连接已断开")
        self._context = None
        self._client = None

    async def list_tools(self) -> List[Dict[str, Any]]:
        await self.connect()
        assert self._client is not None

        try:
            result = await self._client.list_tools()
        except Exception as exc:
            raise ExternalServiceError("MCP list_tools 调用失败", details={"error": str(exc)}) from exc

        tools = getattr(result, "tools", result)
        if not isinstance(tools, list):
            return []

        # 统一输出为 dict 结构，避免上层依赖 fastmcp 返回对象细节。
        normalized: List[Dict[str, Any]] = []
        for tool in tools:
            if isinstance(tool, dict):
                normalized.append(
                    {
                        "name": str(tool.get("name", "")),
                        "description": str(tool.get("description", "")),
                        "input_schema": tool.get("inputSchema", tool.get("input_schema", {})),
                    }
                )
                continue

            normalized.append(
                {
                    "name": str(getattr(tool, "name", "")),
                    "description": str(getattr(tool, "description", "") or ""),
                    "input_schema": getattr(tool, "inputSchema", getattr(tool, "input_schema", {})),
                }
            )

        return normalized

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        await self.connect()
        assert self._client is not None

        try:
            result = await self._client.call_tool(tool_name, arguments)
        except Exception as exc:
            raise ExternalServiceError(
                "MCP call_tool 调用失败",
                details={"tool_name": tool_name, "error": str(exc)},
            ) from exc

        # 工具结果做一次标准化，屏蔽 TextContent / ToolResult 等协议对象差异。
        return self._normalize_tool_result(result)

    @staticmethod
    def _normalize_tool_result(result: Any) -> Any:
        if isinstance(result, (dict, list, str, int, float, bool)) or result is None:
            return result

        content = getattr(result, "content", None)
        if content is None:
            if hasattr(result, "model_dump"):
                try:
                    return result.model_dump()
                except Exception:
                    return str(result)
            return str(result)

        normalized_items: List[Any] = []
        if not isinstance(content, list):
            content = [content]

        for item in content:
            if isinstance(item, (dict, list, str, int, float, bool)) or item is None:
                normalized_items.append(item)
                continue

            for attr in ("text", "data", "json", "value"):
                value = getattr(item, attr, None)
                if value is not None:
                    normalized_items.append(value)
                    break
            else:
                if hasattr(item, "model_dump"):
                    try:
                        normalized_items.append(item.model_dump())
                    except Exception:
                        normalized_items.append(str(item))
                else:
                    normalized_items.append(str(item))

        if len(normalized_items) == 1:
            return normalized_items[0]
        return normalized_items
