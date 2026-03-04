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

    def test_parse_legacy_key_value_format(self) -> None:
        content, calls = parse_output("[TOOL_CALL:amap_maps_text_search:keywords=历史文化,city=北京]")
        self.assertEqual(len(calls), 1)
        self.assertIn("TOOL_CALL", content)
        self.assertEqual(calls[0].tool_name, "search_poi")
        self.assertEqual(calls[0].arguments["keywords"], "历史文化")
        self.assertEqual(calls[0].arguments["city"], "北京")
        self.assertTrue(calls[0].arguments["citylimit"])

    def test_parse_legacy_plain_text_parameter(self) -> None:
        _, calls = parse_output("[TOOL_CALL:amap_maps_weather:北京]")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].tool_name, "get_weather")
        self.assertEqual(calls[0].arguments["city"], "北京")

    def test_parse_legacy_route_tool_mapping(self) -> None:
        _, calls = parse_output(
            "[TOOL_CALL:maps_direction_driving_by_address:origin_address=天安门,destination_address=故宫]"
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].tool_name, "plan_route")
        self.assertEqual(calls[0].arguments["origin_address"], "天安门")
        self.assertEqual(calls[0].arguments["destination_address"], "故宫")
        self.assertEqual(calls[0].arguments["route_type"], "driving")

    def test_parse_plain_text(self) -> None:
        content, calls = parse_output("这是普通文本")
        self.assertEqual(content, "这是普通文本")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
