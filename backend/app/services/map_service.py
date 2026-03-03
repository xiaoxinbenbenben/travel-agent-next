"""地图相关服务。"""

from __future__ import annotations

from datetime import date
from typing import List

from app.schemas.map import POIInfo, RouteInfo
from app.schemas.trip import WeatherInfo


class MapService:
    """地图服务占位实现。后续替换为 MCP 高德调用。"""

    def search_poi(self, keywords: str, city: str, citylimit: bool = True) -> List[POIInfo]:
        _ = citylimit
        return [
            POIInfo(
                id=f"{city}-{keywords}-001",
                name=f"{keywords}（示例）",
                type="景点",
                address=f"{city}核心区域",
                location={"longitude": 116.397428, "latitude": 39.90923},
                tel=None,
            )
        ]

    def get_weather(self, city: str) -> List[WeatherInfo]:
        today = date.today().isoformat()
        return [
            WeatherInfo(
                date=today,
                day_weather=f"{city}晴",
                night_weather=f"{city}多云",
                day_temp=26,
                night_temp=18,
                wind_direction="东北",
                wind_power="3级",
            )
        ]

    def plan_route(
        self,
        *,
        origin_address: str,
        destination_address: str,
        origin_city: str | None = None,
        destination_city: str | None = None,
        route_type: str = "walking",
    ) -> RouteInfo:
        _ = origin_city, destination_city
        return RouteInfo(
            distance=3200.0,
            duration=2400,
            route_type=route_type,
            description=f"从“{origin_address}”到“{destination_address}”的{route_type}路线（示例）",
        )

    def get_poi_detail(self, poi_id: str) -> dict:
        return {
            "id": poi_id,
            "name": f"POI-{poi_id}",
            "address": "示例地址",
            "location": "116.397428,39.90923",
        }


_map_service = MapService()


def get_map_service() -> MapService:
    return _map_service

