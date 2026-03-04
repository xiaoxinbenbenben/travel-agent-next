"""Trip API 契约测试。"""

import os
import unittest

from fastapi.testclient import TestClient

# 在导入 app 前注入必要环境变量，避免启动期配置校验失败。
os.environ["AMAP_API_KEY"] = "test-amap-key"
os.environ["AMAP_MCP_MOCK"] = "true"

from app.main import app
from app.core.config import get_settings
from app.integrations.mcp.amap_client import get_amap_mcp_client
import app.services.map_service as map_service_module


class TestTripApiContract(unittest.TestCase):
    """/api/trip/plan 契约测试。"""

    def setUp(self) -> None:
        # 测试隔离：重置缓存与单例，确保按当前环境变量初始化。
        get_settings.cache_clear()
        get_amap_mcp_client.cache_clear()
        map_service_module._map_service = None
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
        self.assertEqual(len(data["days"]), 3)
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
        self.assertGreaterEqual(first_day["hotel"]["estimated_cost"], 0)

        self.assertGreaterEqual(len(first_day["meals"]), 3)
        self.assertIn("type", first_day["meals"][0])
        self.assertIn("estimated_cost", first_day["meals"][0])

        self.assertIsInstance(data["weather_info"][0], dict)
        self.assertIn("date", data["weather_info"][0])
        self.assertIn("day_weather", data["weather_info"][0])

        budget = data["budget"]
        self.assertIn("total_attractions", budget)
        self.assertIn("total_hotels", budget)
        self.assertIn("total_meals", budget)
        self.assertIn("total_transportation", budget)
        self.assertIn("total", budget)
        self.assertEqual(
            budget["total"],
            budget["total_attractions"]
            + budget["total_hotels"]
            + budget["total_meals"]
            + budget["total_transportation"],
        )

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
