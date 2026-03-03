"""统一业务异常定义与 HTTP 映射。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from fastapi import HTTPException


@dataclass
class AppError(Exception):
    """应用层基础异常。"""

    message: str
    error_code: str = "APP_ERROR"
    status_code: int = 500
    details: Dict[str, Any] = field(default_factory=dict)

    def to_http_exception(self) -> HTTPException:
        detail: Dict[str, Any] = {
            "success": False,
            "message": self.message,
            "error_code": self.error_code,
        }
        if self.details:
            detail["details"] = self.details
        return HTTPException(status_code=self.status_code, detail=detail)


class ValidationError(AppError):
    """参数校验异常。"""

    def __init__(self, message: str, *, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details or {},
        )


class NotFoundError(AppError):
    """资源不存在异常。"""

    def __init__(self, message: str, *, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=404,
            details=details or {},
        )


class ExternalServiceError(AppError):
    """外部服务调用异常。"""

    def __init__(self, message: str, *, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details=details or {},
        )


class ToolNotFoundError(AppError):
    """工具未注册异常。"""

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            message=f"工具未注册: {tool_name}",
            error_code="TOOL_NOT_FOUND",
            status_code=404,
            details={"tool_name": tool_name},
        )


class ToolValidationError(AppError):
    """工具参数校验异常。"""

    def __init__(self, tool_name: str, message: str) -> None:
        super().__init__(
            message=message,
            error_code="TOOL_VALIDATION_ERROR",
            status_code=400,
            details={"tool_name": tool_name},
        )


class ToolExecutionError(AppError):
    """工具执行异常。"""

    def __init__(self, tool_name: str, message: str) -> None:
        super().__init__(
            message=message,
            error_code="TOOL_EXECUTION_ERROR",
            status_code=500,
            details={"tool_name": tool_name},
        )


def to_http_exception(exc: Exception) -> HTTPException:
    """将任意异常转换为 HTTPException。"""
    if isinstance(exc, AppError):
        return exc.to_http_exception()

    return HTTPException(
        status_code=500,
        detail={
            "success": False,
            "message": str(exc),
            "error_code": "INTERNAL_SERVER_ERROR",
        },
    )

