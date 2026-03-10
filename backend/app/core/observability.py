"""日志与观测辅助。"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from time import perf_counter
from typing import Iterator

from app.core.config import Settings

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(level_text: str) -> None:
    """初始化全局 logging 配置。"""
    level = getattr(logging, str(level_text).upper(), logging.INFO)
    root_logger = logging.getLogger()

    if not root_logger.handlers:
        logging.basicConfig(level=level, format=_LOG_FORMAT)

    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level)


def _status_text(value: str) -> str:
    return "已配置" if value else "未配置"


def build_startup_banner(settings: Settings) -> str:
    """构造应用启动摘要日志。"""
    return (
        "\n"
        + "=" * 60
        + "\n"
        + f"🚀 {settings.app_name} v{settings.app_version}\n"
        + "=" * 60
        + "\n"
        + f"应用名称: {settings.app_name}\n"
        + f"版本: {settings.app_version}\n"
        + f"服务器: {settings.host}:{settings.port}\n"
        + f"高德地图API Key: {_status_text(settings.amap_api_key)}\n"
        + f"LLM API Key: {_status_text(settings.llm_api_key)}\n"
        + f"LLM Base URL: {settings.llm_base_url}\n"
        + f"LLM Model: {settings.llm_model_id}\n"
        + f"日志级别: {settings.log_level}\n"
        + "\n"
        + "=" * 60
        + "\n"
        + "📚 API文档: http://localhost:"
        + f"{settings.port}/docs\n"
        + "📖 ReDoc文档: http://localhost:"
        + f"{settings.port}/redoc\n"
        + "=" * 60
        + "\n"
    )


def build_shutdown_banner() -> str:
    """构造应用关闭日志。"""
    return "\n" + "=" * 60 + "\n👋 应用正在关闭...\n" + "=" * 60 + "\n"


@contextmanager
def log_duration(
    logger: logging.Logger,
    label: str,
    *,
    start_message: str | None = None,
    success_message: str | None = None,
) -> Iterator[None]:
    """为阶段打开始/结束耗时日志。"""
    started_at = perf_counter()
    logger.info(start_message or f"{label}开始")
    try:
        yield
    except Exception:
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.exception("%s失败 | 耗时 %.2f ms", label, elapsed_ms)
        raise
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info("%s | 耗时 %.2f ms", success_message or f"{label}完成", elapsed_ms)
