"""Agent 解析器测试。"""

import unittest

from app.agent.parser import parse_output


class TestAgentParser(unittest.TestCase):
    """解析器测试。"""

    def test_parse_json_single_call(self) -> None:
        content, calls = parse_output('{"tool_name":"search_poi","arguments":{"city":"北京"}}')
        self.assertEqual(content, "")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].tool_name, "search_poi")
        self.assertEqual(calls[0].arguments["city"], "北京")

    def test_parse_json_list_call(self) -> None:
        content, calls = parse_output(
            '[{"tool_name":"a","arguments":{}},{"tool_name":"b","arguments":{"x":1}}]'
        )
        self.assertEqual(content, "")
        self.assertEqual([item.tool_name for item in calls], ["a", "b"])

    def test_parse_legacy_tool_call(self) -> None:
        content, calls = parse_output('先查一下 [TOOL_CALL:search_weather{"city":"北京"}]')
        self.assertIn("TOOL_CALL", content)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].tool_name, "search_weather")
        self.assertEqual(calls[0].arguments["city"], "北京")

    def test_parse_plain_text(self) -> None:
        content, calls = parse_output("这是普通文本")
        self.assertEqual(content, "这是普通文本")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
