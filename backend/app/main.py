"""FastAPI 入口。"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import trip as trip_routes
from app.core import ConfigError, get_settings, validate_settings


logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时执行配置校验。"""
    try:
        warnings = validate_settings(settings)
    except ConfigError:
        logger.exception("配置校验失败，服务终止启动")
        raise

    for warning in warnings:
        logger.warning(warning)

    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trip_routes.router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    """基础健康检查接口。"""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }
