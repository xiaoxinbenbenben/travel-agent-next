"""Map/POI 相关数据模型。"""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.trip import WeatherInfo


class Location(BaseModel):
    """地理位置。"""

    longitude: float = Field(..., description="经度")
    latitude: float = Field(..., description="纬度")


class POISearchRequest(BaseModel):
    """POI 搜索请求。"""

    keywords: str = Field(..., description="搜索关键词")
    city: str = Field(..., description="城市")
    citylimit: bool = Field(default=True, description="是否限制在城市范围内")


class POIInfo(BaseModel):
    """POI 信息。"""

    id: str = Field(..., description="POI ID")
    name: str = Field(..., description="名称")
    type: str = Field(default="", description="类型")
    address: str = Field(default="", description="地址")
    location: Location = Field(..., description="经纬度坐标")
    tel: Optional[str] = Field(default=None, description="电话")


class POISearchResponse(BaseModel):
    """POI 搜索响应。"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: List[POIInfo] = Field(default_factory=list, description="POI 列表")


class RouteRequest(BaseModel):
    """路线规划请求。"""

    origin_address: str = Field(..., description="起点地址")
    destination_address: str = Field(..., description="终点地址")
    origin_city: Optional[str] = Field(default=None, description="起点城市")
    destination_city: Optional[str] = Field(default=None, description="终点城市")
    route_type: str = Field(default="walking", description="路线类型: walking/driving/transit")


class RouteInfo(BaseModel):
    """路线信息。"""

    distance: float = Field(..., description="距离(米)")
    duration: int = Field(..., description="时间(秒)")
    route_type: str = Field(..., description="路线类型")
    description: str = Field(..., description="路线描述")


class RouteResponse(BaseModel):
    """路线规划响应。"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: Optional[RouteInfo] = Field(default=None, description="路线信息")


class WeatherResponse(BaseModel):
    """天气查询响应。"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: List[WeatherInfo] = Field(default_factory=list, description="天气信息")


class POIDetailResponse(BaseModel):
    """POI 详情响应。"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: Optional[dict] = Field(default=None, description="POI 详情")


class PhotoData(BaseModel):
    """图片信息。"""

    name: str = Field(..., description="景点名称")
    photo_url: Optional[str] = Field(default=None, description="图片 URL")


class POIPhotoResponse(BaseModel):
    """POI 图片响应。"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: PhotoData = Field(..., description="图片信息")

