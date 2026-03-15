"""地图相关服务。"""

from __future__ import annotations

from typing import List

from app.integrations.mcp import AmapMCPClient, get_amap_mcp_client
from app.schemas.map import POIInfo, RouteInfo
from app.schemas.trip import WeatherInfo


class MapService:
    """地图服务：基于 AmapMCPClient 封装业务模型。"""

    def __init__(self, client: AmapMCPClient) -> None:
        self.client = client

    async def search_poi(
        self,
        keywords: str,
        city: str,
        citylimit: bool = True,
        enrich_details: bool = True,
    ) -> List[POIInfo]:
        payload = await self.client.search_poi(
            keywords=keywords,
            city=city,
            citylimit=citylimit,
            enrich_details=enrich_details,
        )
        # 服务层统一做 schema 校验，路由层拿到的始终是稳定模型。
        return [POIInfo.model_validate(item) for item in payload]

    async def get_weather(self, city: str) -> List[WeatherInfo]:
        payload = await self.client.get_weather(city=city)
        return [WeatherInfo.model_validate(item) for item in payload]

    async def plan_route(
        self,
        *,
        origin_address: str,
        destination_address: str,
        origin_city: str | None = None,
        destination_city: str | None = None,
        route_type: str = "walking",
    ) -> RouteInfo:
        payload = await self.client.plan_route(
            origin_address=origin_address,
            destination_address=destination_address,
            origin_city=origin_city,
            destination_city=destination_city,
            route_type=route_type,
        )
        return RouteInfo.model_validate(payload)

    async def get_poi_detail(self, poi_id: str) -> dict:
        return await self.client.get_poi_detail(poi_id=poi_id)


_map_service: MapService | None = None


def get_map_service() -> MapService:
    global _map_service
    if _map_service is None:
        # 复用单例，保证整个应用共享同一个 AmapMCPClient。
        _map_service = MapService(client=get_amap_mcp_client())
    return _map_service
