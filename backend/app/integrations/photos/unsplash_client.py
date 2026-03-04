"""Unsplash 客户端封装。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core import ExternalServiceError, ValidationError, get_settings


@dataclass(frozen=True)
class UnsplashClient:
    """最小 Unsplash 搜图客户端。"""

    access_key: str
    base_url: str = "https://api.unsplash.com"
    timeout_seconds: int = 8

    def search_photos(self, query: str, per_page: int = 5) -> List[Dict[str, Any]]:
        if not query.strip():
            return []

        params = urlencode(
            {
                "query": query,
                "per_page": max(1, min(per_page, 30)),
                "client_id": self.access_key,
            }
        )
        url = f"{self.base_url}/search/photos?{params}"
        request = Request(url=url, method="GET")

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                payload = response.read().decode("utf-8")
            data = json.loads(payload)
        except Exception as exc:
            raise ExternalServiceError(
                "Unsplash 查询失败",
                details={"query": query, "error": str(exc)},
            ) from exc

        if not isinstance(data, dict):
            return []
        results = data.get("results", [])
        if not isinstance(results, list):
            return []

        photos: List[Dict[str, Any]] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            urls = item.get("urls", {})
            user = item.get("user", {})
            if not isinstance(urls, dict):
                urls = {}
            if not isinstance(user, dict):
                user = {}
            photos.append(
                {
                    "id": item.get("id"),
                    "url": urls.get("regular"),
                    "thumb": urls.get("thumb"),
                    "description": item.get("description") or item.get("alt_description"),
                    "photographer": user.get("name"),
                }
            )
        return photos

    def get_photo_url(self, query: str) -> str | None:
        photos = self.search_photos(query=query, per_page=1)
        if not photos:
            return None
        first = photos[0]
        url = first.get("url")
        if isinstance(url, str) and url:
            return url
        return None


def build_unsplash_client() -> UnsplashClient:
    """根据配置创建 UnsplashClient。"""
    settings = get_settings()
    if not settings.unsplash_access_key:
        raise ValidationError("UNSPLASH_ACCESS_KEY 未配置，无法创建 UnsplashClient")
    return UnsplashClient(access_key=settings.unsplash_access_key)

