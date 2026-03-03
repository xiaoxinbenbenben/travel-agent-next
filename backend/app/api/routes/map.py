"""Map 路由。"""

from fastapi import APIRouter, Query

from app.core import AppError, to_http_exception
from app.schemas import (
    POISearchResponse,
    RouteRequest,
    RouteResponse,
    WeatherResponse,
)
from app.services import get_map_service

router = APIRouter(prefix="/map", tags=["地图服务"])


@router.get("/poi", response_model=POISearchResponse, summary="搜索POI")
async def search_poi(
    keywords: str = Query(..., description="搜索关键词"),
    city: str = Query(..., description="城市"),
    citylimit: bool = Query(True, description="是否限制在城市范围内"),
) -> POISearchResponse:
    try:
        # 路由层只做参数接收与响应编排，业务细节下沉到 service。
        service = get_map_service()
        pois = await service.search_poi(keywords=keywords, city=city, citylimit=citylimit)
        return POISearchResponse(success=True, message="POI搜索成功", data=pois)
    except Exception as exc:
        # 统一异常转换，保持 API 错误结构一致。
        raise to_http_exception(exc if isinstance(exc, AppError) else AppError(str(exc))) from exc


@router.get("/weather", response_model=WeatherResponse, summary="查询天气")
async def get_weather(city: str = Query(..., description="城市名称")) -> WeatherResponse:
    try:
        service = get_map_service()
        weather = await service.get_weather(city)
        return WeatherResponse(success=True, message="天气查询成功", data=weather)
    except Exception as exc:
        raise to_http_exception(exc if isinstance(exc, AppError) else AppError(str(exc))) from exc


@router.post("/route", response_model=RouteResponse, summary="规划路线")
async def plan_route(request: RouteRequest) -> RouteResponse:
    try:
        service = get_map_service()
        route = await service.plan_route(
            origin_address=request.origin_address,
            destination_address=request.destination_address,
            origin_city=request.origin_city,
            destination_city=request.destination_city,
            route_type=request.route_type,
        )
        return RouteResponse(success=True, message="路线规划成功", data=route)
    except Exception as exc:
        raise to_http_exception(exc if isinstance(exc, AppError) else AppError(str(exc))) from exc
