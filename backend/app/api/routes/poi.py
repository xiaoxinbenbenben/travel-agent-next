"""POI 路由。"""

from fastapi import APIRouter, Query

from app.core import AppError, to_http_exception
from app.schemas import POIDetailResponse, POIPhotoResponse
from app.schemas.map import PhotoData
from app.services import get_map_service, get_photo_service

router = APIRouter(prefix="/poi", tags=["POI"])


@router.get("/detail/{poi_id}", response_model=POIDetailResponse, summary="获取POI详情")
async def get_poi_detail(poi_id: str) -> POIDetailResponse:
    try:
        # 详情查询委托给 map service，路由保持轻量。
        service = get_map_service()
        detail = await service.get_poi_detail(poi_id)
        return POIDetailResponse(success=True, message="获取POI详情成功", data=detail)
    except Exception as exc:
        raise to_http_exception(exc if isinstance(exc, AppError) else AppError(str(exc))) from exc


@router.get("/search", summary="搜索POI")
async def search_poi(
    keywords: str = Query(..., description="关键词"),
    city: str = Query("北京", description="城市"),
) -> dict:
    try:
        # `/api/poi/search` 保持与旧项目返回结构兼容（dict 包装）。
        service = get_map_service()
        result = await service.search_poi(keywords=keywords, city=city)
        return {
            "success": True,
            "message": "搜索成功",
            "data": [item.model_dump() for item in result],
        }
    except Exception as exc:
        raise to_http_exception(exc if isinstance(exc, AppError) else AppError(str(exc))) from exc


@router.get("/photo", response_model=POIPhotoResponse, summary="获取景点图片")
async def get_attraction_photo(name: str = Query(..., description="景点名称")) -> POIPhotoResponse:
    try:
        # 图片服务独立于地图查询，便于后续替换 Unsplash 实现。
        service = get_photo_service()
        url = service.get_attraction_photo(name)
        return POIPhotoResponse(
            success=True,
            message="获取图片成功",
            data=PhotoData(name=name, photo_url=url),
        )
    except Exception as exc:
        raise to_http_exception(exc if isinstance(exc, AppError) else AppError(str(exc))) from exc
