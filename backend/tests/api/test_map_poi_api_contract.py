"""Map/POI API 契约测试。"""

import os
import unittest

from fastapi.testclient import TestClient

os.environ.setdefault("AMAP_API_KEY", "test-amap-key")

from app.main import app


class TestMapPoiApiContract(unittest.TestCase):
    """Map/POI 契约测试。"""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_map_poi_search(self) -> None:
        response = self.client.get("/api/map/poi", params={"keywords": "故宫", "city": "北京"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertIsInstance(body["data"], list)
        self.assertGreaterEqual(len(body["data"]), 1)
        self.assertIn("name", body["data"][0])
        self.assertIn("location", body["data"][0])

    def test_map_weather(self) -> None:
        response = self.client.get("/api/map/weather", params={"city": "北京"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertIsInstance(body["data"], list)

    def test_map_route(self) -> None:
        payload = {
            "origin_address": "天安门",
            "destination_address": "故宫",
            "origin_city": "北京",
            "destination_city": "北京",
            "route_type": "walking",
        }
        response = self.client.post("/api/map/route", json=payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertIn("distance", body["data"])
        self.assertIn("duration", body["data"])

    def test_poi_photo(self) -> None:
        response = self.client.get("/api/poi/photo", params={"name": "故宫"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertIn("photo_url", body["data"])


if __name__ == "__main__":
    unittest.main()
