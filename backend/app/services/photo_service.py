"""图片相关服务。"""

from __future__ import annotations

from urllib.parse import quote_plus


class PhotoService:
    """图片服务占位实现。后续替换为 Unsplash 接口调用。"""

    def get_attraction_photo(self, name: str) -> str:
        keyword = quote_plus(name)
        return f"https://source.unsplash.com/featured/?{keyword}"


_photo_service = PhotoService()


def get_photo_service() -> PhotoService:
    return _photo_service

