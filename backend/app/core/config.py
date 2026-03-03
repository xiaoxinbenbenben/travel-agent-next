"""应用配置读取与校验。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List


class ConfigError(ValueError):
    """配置异常。"""


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _load_dotenv_file(env_file: Path) -> None:
    # 解析策略：仅加载当前进程中不存在的键，外部注入的环境变量优先级更高。
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue

        key, value = raw.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue

        os.environ[key] = _strip_quotes(value.strip())


def _to_bool(raw: str | None, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _to_int(raw: str | None, default: int) -> int:
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """应用配置对象。"""

    app_name: str = "Travel Agent Next API"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    amap_api_key: str = ""
    unsplash_access_key: str = ""
    unsplash_secret_key: str = ""
    llm_model_id: str = "gpt-4o-mini"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout: int = 60
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @classmethod
    def from_env(cls, load_dotenv: bool = True) -> "Settings":
        if load_dotenv:
            _load_dotenv_file(_project_root() / ".env")

        llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        llm_base_url = (
            os.getenv("LLM_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        )
        llm_model_id = os.getenv("LLM_MODEL_ID") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

        return cls(
            app_name=os.getenv("APP_NAME", "Travel Agent Next API"),
            app_version=os.getenv("APP_VERSION", "0.1.0"),
            debug=_to_bool(os.getenv("DEBUG"), default=False),
            host=os.getenv("HOST", "0.0.0.0"),
            port=_to_int(os.getenv("PORT"), 8000),
            cors_origins=os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://localhost:3000",
            ),
            amap_api_key=os.getenv("AMAP_API_KEY", ""),
            unsplash_access_key=os.getenv("UNSPLASH_ACCESS_KEY", ""),
            unsplash_secret_key=os.getenv("UNSPLASH_SECRET_KEY", ""),
            llm_model_id=llm_model_id,
            llm_api_key=llm_api_key,
            llm_base_url=llm_base_url,
            llm_timeout=_to_int(os.getenv("LLM_TIMEOUT"), 60),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


def validate_settings(settings: Settings) -> List[str]:
    """校验关键配置，返回告警列表；若存在阻断项则抛出 ConfigError。"""
    errors: List[str] = []
    warnings: List[str] = []

    if not settings.amap_api_key:
        errors.append("AMAP_API_KEY 未配置")

    if not settings.llm_api_key:
        warnings.append("LLM_API_KEY 或 OPENAI_API_KEY 未配置，LLM 功能可能不可用")

    if errors:
        message = "配置错误:\n" + "\n".join(f"  - {item}" for item in errors)
        raise ConfigError(message)

    return warnings


@lru_cache()
def get_settings() -> Settings:
    return Settings.from_env(load_dotenv=True)
