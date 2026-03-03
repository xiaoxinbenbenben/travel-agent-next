"""Trip API 契约测试。"""

import os
import unittest

from fastapi.testclient import TestClient

# 在导入 app 前注入必要环境变量，避免启动期配置校验失败。
os.environ.setdefault("AMAP_API_KEY", "test-amap-key")

from app.main import app


class TestTripApiContract(unittest.TestCase):
    """/api/trip/plan 契约测试。"""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_plan_trip_success_contract(self) -> None:
        payload = {
            "city": "北京",
            "start_date": "2026-04-01",
            "end_date": "2026-04-03",
            "travel_days": 3,
            "transportation": "公共交通",
            "accommodation": "经济型酒店",
            "preferences": ["历史文化", "美食"],
            "free_text_input": "希望多安排博物馆",
        }

        response = self.client.post("/api/trip/plan", json=payload)
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertTrue(body["success"])
        self.assertIn("message", body)
        self.assertIn("data", body)

        data = body["data"]
        self.assertEqual(data["city"], "北京")
        self.assertEqual(data["start_date"], "2026-04-01")
        self.assertEqual(data["end_date"], "2026-04-03")
        self.assertIsInstance(data["days"], list)
        self.assertGreaterEqual(len(data["days"]), 1)
        self.assertIsInstance(data["weather_info"], list)
        self.assertIn("overall_suggestions", data)
        self.assertIn("budget", data)

        first_day = data["days"][0]
        self.assertEqual(first_day["date"], "2026-04-01")
        self.assertEqual(first_day["day_index"], 0)
        self.assertIn("description", first_day)
        self.assertEqual(first_day["transportation"], "公共交通")
        self.assertEqual(first_day["accommodation"], "经济型酒店")
        self.assertIsInstance(first_day["attractions"], list)
        self.assertIsInstance(first_day["meals"], list)
        self.assertIn("hotel", first_day)
        self.assertIsInstance(first_day["hotel"], dict)
        self.assertIn("name", first_day["hotel"])
        self.assertIn("address", first_day["hotel"])
        self.assertIn("estimated_cost", first_day["hotel"])

    def test_plan_trip_invalid_request(self) -> None:
        payload = {
            "city": "北京",
            "start_date": "2026-04-01",
            "end_date": "2026-04-03",
            "travel_days": 0,
            "transportation": "公共交通",
            "accommodation": "经济型酒店",
            "preferences": [],
            "free_text_input": "",
        }

        response = self.client.post("/api/trip/plan", json=payload)
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
