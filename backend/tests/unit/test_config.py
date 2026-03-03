"""配置模块测试。"""

import os
import unittest
from unittest.mock import patch

from app.core.config import ConfigError, Settings, validate_settings


class TestSettings(unittest.TestCase):
    """配置读取与校验测试。"""

    def test_cors_origins_list_split_and_strip(self) -> None:
        settings = Settings(
            cors_origins="http://a.com, http://b.com ,,http://c.com",
        )
        self.assertEqual(
            settings.cors_origins_list,
            ["http://a.com", "http://b.com", "http://c.com"],
        )

    def test_validate_settings_requires_amap_api_key(self) -> None:
        settings = Settings(amap_api_key="", llm_api_key="test-key")
        with self.assertRaises(ConfigError):
            validate_settings(settings)

    def test_validate_settings_warns_when_llm_api_key_missing(self) -> None:
        settings = Settings(amap_api_key="amap-key", llm_api_key="")
        warnings = validate_settings(settings)
        self.assertTrue(any("LLM_API_KEY" in item for item in warnings))

    def test_from_env_loads_legacy_keys(self) -> None:
        env = {
            "LLM_MODEL_ID": "qwen-test",
            "LLM_API_KEY": "llm-key",
            "LLM_BASE_URL": "https://example.com/v1",
            "LLM_TIMEOUT": "99",
            "HOST": "127.0.0.1",
            "PORT": "9000",
            "CORS_ORIGINS": "http://localhost:5173,http://localhost:3000",
            "LOG_LEVEL": "DEBUG",
            "UNSPLASH_ACCESS_KEY": "access",
            "UNSPLASH_SECRET_KEY": "secret",
            "AMAP_API_KEY": "amap-key",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings.from_env(load_dotenv=False)

        self.assertEqual(settings.llm_model_id, "qwen-test")
        self.assertEqual(settings.llm_api_key, "llm-key")
        self.assertEqual(settings.llm_base_url, "https://example.com/v1")
        self.assertEqual(settings.llm_timeout, 99)
        self.assertEqual(settings.host, "127.0.0.1")
        self.assertEqual(settings.port, 9000)
        self.assertEqual(settings.log_level, "DEBUG")
        self.assertEqual(settings.unsplash_access_key, "access")
        self.assertEqual(settings.unsplash_secret_key, "secret")
        self.assertEqual(settings.amap_api_key, "amap-key")


if __name__ == "__main__":
    unittest.main()
