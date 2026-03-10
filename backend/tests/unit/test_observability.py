"""日志辅助能力测试。"""

import logging
import unittest

from app.core.config import Settings
from app.core.observability import build_shutdown_banner, build_startup_banner, log_duration


class TestObservability(unittest.TestCase):
    """日志辅助模块测试。"""

    def test_build_startup_banner_contains_config_summary(self) -> None:
        settings = Settings(
            app_name="Travel Agent Next API",
            app_version="0.1.0",
            host="0.0.0.0",
            port=8000,
            amap_api_key="test-key",
            llm_api_key="llm-key",
            llm_base_url="https://example.com/v1",
            llm_model_id="test-model",
            log_level="DEBUG",
        )

        banner = build_startup_banner(settings)

        self.assertIn("🚀 Travel Agent Next API v0.1.0", banner)
        self.assertIn("服务器: 0.0.0.0:8000", banner)
        self.assertIn("高德地图API Key: 已配置", banner)
        self.assertIn("LLM API Key: 已配置", banner)
        self.assertIn("LLM Base URL: https://example.com/v1", banner)
        self.assertIn("LLM Model: test-model", banner)
        self.assertIn("日志级别: DEBUG", banner)
        self.assertIn("API文档", banner)
        self.assertIn("ReDoc文档", banner)

    def test_build_shutdown_banner_contains_goodbye_message(self) -> None:
        banner = build_shutdown_banner()
        self.assertIn("应用正在关闭", banner)

    def test_log_duration_logs_start_and_finish(self) -> None:
        logger = logging.getLogger("tests.observability")
        with self.assertLogs("tests.observability", level="INFO") as captured:
            with log_duration(logger, "测试阶段"):
                pass

        joined = "\n".join(captured.output)
        self.assertIn("测试阶段开始", joined)
        self.assertIn("测试阶段完成", joined)
        self.assertIn("耗时", joined)
