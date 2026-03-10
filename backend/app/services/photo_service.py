"""图片相关服务。"""

from __future__ import annotations

from urllib.parse import quote_plus

from app.core import ExternalServiceError, get_settings
from app.integrations.photos import UnsplashClient


class PhotoService:
    """图片服务：优先 Unsplash，失败时降级到 source.unsplash.com。"""

    def __init__(self, client: UnsplashClient | None = None) -> None:
        self.client = client

    def get_attraction_photo(self, name: str) -> str:
        query = name.strip()
        if not query:
            query = "travel"

        if self.client is not None:
            try:
                url = self.client.get_photo_url(query)
            except ExternalServiceError:
                url = None
            if isinstance(url, str) and url:
                return url

        keyword = quote_plus(query)
        return f"https://source.unsplash.com/featured/?{keyword}"


def _build_default_photo_service() -> PhotoService:
    settings = get_settings()
    client: UnsplashClient | None = None
    if settings.unsplash_access_key:
        client = UnsplashClient(access_key=settings.unsplash_access_key)
    return PhotoService(client=client)


_photo_service: PhotoService | None = None


def get_photo_service() -> PhotoService:
    global _photo_service
    if _photo_service is None:
        _photo_service = _build_default_photo_service()
    return _photo_service
