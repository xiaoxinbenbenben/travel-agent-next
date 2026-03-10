"""Trip 路由日志测试。"""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.api.routes.trip import plan_trip
from app.schemas import TripPlan, TripRequest


class TestTripRouteLogging(unittest.TestCase):
    """验证 trip 路由日志。"""

    def test_plan_trip_logs_request_and_success(self) -> None:
        request = TripRequest(
            city="北京",
            start_date="2026-04-01",
            end_date="2026-04-03",
            travel_days=3,
            transportation="公共交通",
            accommodation="经济型酒店",
            preferences=["自然景观", "历史文化"],
            free_text_input="想去故宫，长城",
        )
        plan = TripPlan(
            city="北京",
            start_date="2026-04-01",
            end_date="2026-04-03",
            days=[],
            weather_info=[],
            overall_suggestions="测试建议",
            budget=None,
        )

        with (
            patch("app.api.routes.trip.build_trip_plan", new=AsyncMock(return_value=plan)),
            self.assertLogs("app.api.routes.trip", level="INFO") as captured,
        ):
            response = asyncio.run(plan_trip(request))

        self.assertTrue(response.success)
        joined = "\n".join(captured.output)
        self.assertIn("收到旅行规划请求", joined)
        self.assertIn("开始生成旅行计划", joined)
        self.assertIn("旅行计划生成成功", joined)
        self.assertIn("总耗时", joined)
