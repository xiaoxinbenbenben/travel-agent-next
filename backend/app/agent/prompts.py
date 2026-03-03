"""Agent Prompt 模板。"""

TRIP_SYSTEM_PROMPT = (
    "你是旅行规划助手。输出优先使用结构化 JSON 工具调用："
    '{"tool_name":"<name>","arguments":{...}}。'
    "若无需工具，请直接给出可执行建议。"
)

TRIP_USER_PROMPT_TEMPLATE = (
    "目的地: {city}\n"
    "时间: {start_date} 到 {end_date}，共 {travel_days} 天\n"
    "交通: {transportation}\n"
    "住宿: {accommodation}\n"
    "偏好: {preferences}\n"
    "补充要求: {free_text_input}\n"
)

