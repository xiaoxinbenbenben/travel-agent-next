"""FastAPI 入口。"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import (
    ConfigError,
    build_shutdown_banner,
    build_startup_banner,
    configure_logging,
    get_settings,
    validate_settings,
)
from app.api.routes import map as map_routes
from app.api.routes import poi as poi_routes
from app.api.routes import trip as trip_routes

settings = get_settings()

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时执行配置校验。"""
    logger.info(build_startup_banner(settings))
    try:
        warnings = validate_settings(settings)
    except ConfigError:
        logger.exception("❌ 配置验证失败，服务终止启动")
        raise

    for warning in warnings:
        logger.warning(warning)

    logger.info("✅ 配置验证通过")
    yield
    logger.info(build_shutdown_banner())


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
app.include_router(map_routes.router, prefix="/api")
app.include_router(poi_routes.router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    """基础健康检查接口。"""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }
