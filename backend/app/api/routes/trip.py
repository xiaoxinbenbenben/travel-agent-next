"""Trip 路由。"""

from fastapi import APIRouter, HTTPException

from app.schemas import TripPlanResponse, TripRequest
from app.services import build_trip_plan

router = APIRouter(prefix="/trip", tags=["旅行规划"])


@router.post("/plan", response_model=TripPlanResponse, summary="生成旅行计划")
async def plan_trip(request: TripRequest) -> TripPlanResponse:
    """根据输入参数生成旅行计划。"""
    try:
        plan = build_trip_plan(request)
        return TripPlanResponse(success=True, message="旅行计划生成成功", data=plan)
    except Exception as exc:
        # TODO: 接入统一业务异常后，改为按错误类型映射 HTTP 状态码与错误码。
        raise HTTPException(status_code=500, detail=f"生成旅行计划失败: {exc}") from exc
