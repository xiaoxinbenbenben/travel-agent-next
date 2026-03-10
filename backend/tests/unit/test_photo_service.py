"""PhotoService 测试。"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.core import ExternalServiceError
import app.services.photo_service as photo_service_module
from app.services.photo_service import PhotoService, get_photo_service


class _FakeClientOK:
    def get_photo_url(self, query: str) -> str | None:
        return f"https://images.example.com/{query}"


class _FakeClientEmpty:
    def get_photo_url(self, query: str) -> str | None:
        _ = query
        return None


class _FakeClientError:
    def get_photo_url(self, query: str) -> str | None:
        raise ExternalServiceError("boom", details={"query": query})


class TestPhotoService(unittest.TestCase):
    """图片服务行为测试。"""

    def test_prefers_unsplash_client_when_available(self) -> None:
        service = PhotoService(client=_FakeClientOK())  # type: ignore[arg-type]
        url = service.get_attraction_photo("故宫")
        self.assertEqual(url, "https://images.example.com/故宫")

    def test_fallback_when_client_returns_empty(self) -> None:
        service = PhotoService(client=_FakeClientEmpty())  # type: ignore[arg-type]
        url = service.get_attraction_photo("故宫")
        self.assertTrue(url.startswith("https://source.unsplash.com/featured/?"))
        self.assertIn("%E6%95%85%E5%AE%AB", url)

    def test_fallback_when_client_errors(self) -> None:
        service = PhotoService(client=_FakeClientError())  # type: ignore[arg-type]
        url = service.get_attraction_photo("长城")
        self.assertTrue(url.startswith("https://source.unsplash.com/featured/?"))
        self.assertIn("%E9%95%BF%E5%9F%8E", url)

    def test_blank_name_falls_back_to_default_keyword(self) -> None:
        service = PhotoService(client=None)
        url = service.get_attraction_photo("")
        self.assertEqual(url, "https://source.unsplash.com/featured/?travel")

    def test_get_photo_service_builds_singleton_lazily(self) -> None:
        original = photo_service_module._photo_service
        try:
            photo_service_module._photo_service = None
            with patch(
                "app.services.photo_service.get_settings",
                return_value=SimpleNamespace(unsplash_access_key=""),
            ):
                first = get_photo_service()
                second = get_photo_service()
        finally:
            photo_service_module._photo_service = original

        self.assertIs(first, second)
        self.assertIsNone(first.client)


if __name__ == "__main__":
    unittest.main()
