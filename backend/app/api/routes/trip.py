"""Trip 路由。"""

import logging
from time import perf_counter

from fastapi import APIRouter

from app.core import AppError, to_http_exception
from app.schemas import TripPlanResponse, TripRequest
from app.services import build_trip_plan

router = APIRouter(prefix="/trip", tags=["旅行规划"])
logger = logging.getLogger(__name__)


@router.post("/plan", response_model=TripPlanResponse, summary="生成旅行计划")
async def plan_trip(request: TripRequest) -> TripPlanResponse:
    """根据输入参数生成旅行计划。"""
    started_at = perf_counter()
    logger.info(
        "\n%s\n📥 收到旅行规划请求:\n   城市: %s\n   日期: %s - %s\n   天数: %s\n%s\n",
        "=" * 60,
        request.city,
        request.start_date,
        request.end_date,
        request.travel_days,
        "=" * 60,
    )
    try:
        # 入口只负责触发 Trip service，编排逻辑在 service/workflow 内完成。
        logger.info("🚀 开始生成旅行计划...")
        plan = await build_trip_plan(request)
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.info("✅ 旅行计划生成成功,准备返回响应 | 总耗时 %.2f ms", elapsed_ms)
        return TripPlanResponse(success=True, message="旅行计划生成成功", data=plan)
    except Exception as exc:
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.exception("❌ 生成旅行计划失败 | 总耗时 %.2f ms", elapsed_ms)
        # 统一错误映射，避免路由层散落 HTTPException 细节。
        raise to_http_exception(exc if isinstance(exc, AppError) else AppError(str(exc))) from exc
