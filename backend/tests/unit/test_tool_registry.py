"""ToolRegistry 测试。"""

import asyncio
import unittest

from pydantic import BaseModel, Field

from app.agent.tool_registry import ToolRegistry
from app.core import ToolNotFoundError, ToolValidationError


class EchoArgs(BaseModel):
    text: str = Field(..., min_length=1)


class TestToolRegistry(unittest.TestCase):
    """工具注册与分发测试。"""

    def test_dispatch_success(self) -> None:
        registry = ToolRegistry()
        registry.register(
            "echo",
            lambda payload: {"echo": payload["text"]},
            args_model=EchoArgs,
        )
        result = asyncio.run(registry.dispatch("echo", {"text": "hello"}))
        self.assertEqual(result, {"echo": "hello"})

    def test_dispatch_tool_not_found(self) -> None:
        registry = ToolRegistry()
        with self.assertRaises(ToolNotFoundError):
            asyncio.run(registry.dispatch("missing", {}))

    def test_dispatch_validation_error(self) -> None:
        registry = ToolRegistry()
        registry.register("echo", lambda payload: payload, args_model=EchoArgs)
        with self.assertRaises(ToolValidationError):
            asyncio.run(registry.dispatch("echo", {"text": ""}))


if __name__ == "__main__":
    unittest.main()
