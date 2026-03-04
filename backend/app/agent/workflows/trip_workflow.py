"""Trip 工作流编排。"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from app.agent.contracts import AgentRunResult, ToolTrace
from app.agent.prompts import (
    ATTRACTION_SYSTEM_PROMPT,
    ATTRACTION_USER_PROMPT_TEMPLATE,
    HOTEL_SYSTEM_PROMPT,
    HOTEL_USER_PROMPT_TEMPLATE,
    MEAL_SYSTEM_PROMPT,
    MEAL_USER_PROMPT_TEMPLATE,
    PLANNER_SYSTEM_PROMPT,
    WEATHER_SYSTEM_PROMPT,
    WEATHER_USER_PROMPT_TEMPLATE,
)
from app.agent.runtime import MiniAgent
from app.schemas.trip import TripRequest


class TripWorkflow:
    """Trip 编排入口：景点/天气/酒店/美食/图片/总结六阶段。"""

    def __init__(self, agent: MiniAgent) -> None:
        self.agent = agent

    async def run(self, request: TripRequest) -> AgentRunResult:
        all_traces: List[ToolTrace] = []
        preferences = ", ".join(request.preferences) if request.preferences else "城市漫游"

        attraction_stage = await self._run_stage_with_fallback(
            messages=[
                {"role": "system", "content": ATTRACTION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": ATTRACTION_USER_PROMPT_TEMPLATE.format(
                        city=request.city,
                        preferences=preferences,
                    ),
                },
            ],
            required_tool="search_poi",
            fallback_arguments={
                "keywords": request.preferences[0] if request.preferences else "热门景点",
                "city": request.city,
                "citylimit": True,
            },
        )
        all_traces.extend(attraction_stage.traces)

        weather_stage = await self._run_stage_with_fallback(
            messages=[
                {"role": "system", "content": WEATHER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": WEATHER_USER_PROMPT_TEMPLATE.format(city=request.city),
                },
            ],
            required_tool="get_weather",
            fallback_arguments={"city": request.city},
        )
        all_traces.extend(weather_stage.traces)

        hotel_keyword = request.accommodation or "酒店"
        hotel_stage = await self._run_stage_with_fallback(
            messages=[
                {"role": "system", "content": HOTEL_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": HOTEL_USER_PROMPT_TEMPLATE.format(
                        city=request.city,
                        accommodation=hotel_keyword,
                    ),
                },
            ],
            required_tool="search_poi",
            fallback_arguments={
                "keywords": hotel_keyword,
                "city": request.city,
                "citylimit": True,
            },
        )
        all_traces.extend(hotel_stage.traces)

        meal_stage = await self._run_stage_with_fallback(
            messages=[
                {"role": "system", "content": MEAL_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": MEAL_USER_PROMPT_TEMPLATE.format(city=request.city),
                },
            ],
            required_tool="search_poi",
            fallback_arguments={
                "keywords": "美食 餐厅",
                "city": request.city,
                "citylimit": True,
            },
        )
        all_traces.extend(meal_stage.traces)

        attraction_name = self._pick_first_attraction_name(attraction_stage.traces)
        if attraction_name:
            photo_stage = await self._run_stage_with_fallback(
                messages=[
                    {"role": "system", "content": "你是图片助手，调用 get_photo 获取景点图。"},
                    {"role": "user", "content": f"请查询 {attraction_name} 的图片。"},
                ],
                required_tool="get_photo",
                fallback_arguments={"name": attraction_name},
            )
            all_traces.extend(photo_stage.traces)

        summary_payload = {
            "city": request.city,
            "date_range": f"{request.start_date}~{request.end_date}",
            "travel_days": request.travel_days,
            "preferences": request.preferences,
            "tool_traces": [self._trace_to_dict(item) for item in all_traces],
            "free_text_input": request.free_text_input,
        }

        planner_result = await self.agent.run(
            [
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(summary_payload, ensure_ascii=False)},
            ]
        )
        all_traces.extend(planner_result.traces)

        summary = planner_result.content.strip() if planner_result.content else ""
        if not summary:
            summary = self._fallback_summary(request)
        return AgentRunResult(content=summary, traces=all_traces)

    async def _run_stage_with_fallback(
        self,
        *,
        messages: List[Dict[str, str]],
        required_tool: str,
        fallback_arguments: Dict[str, Any],
    ) -> AgentRunResult:
        result = await self.agent.run(messages)
        traces = list(result.traces)
        if any(item.tool_name == required_tool for item in traces):
            return AgentRunResult(content=result.content, traces=traces)

        fallback_result = await self.agent.tool_registry.dispatch(required_tool, fallback_arguments)
        traces.append(
            ToolTrace(
                tool_name=required_tool,
                arguments=fallback_arguments,
                result=fallback_result,
            )
        )
        return AgentRunResult(content=result.content, traces=traces)

    @staticmethod
    def _pick_first_attraction_name(traces: List[ToolTrace]) -> str | None:
        for trace in traces:
            if trace.tool_name != "search_poi" or not isinstance(trace.result, list):
                continue
            for item in trace.result:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
        return None

    @staticmethod
    def _trace_to_dict(trace: ToolTrace) -> Dict[str, Any]:
        return {
            "tool_name": trace.tool_name,
            "arguments": trace.arguments,
            "result": trace.result,
        }

    @staticmethod
    def _fallback_summary(request: TripRequest) -> str:
        return (
            f"已完成 {request.city} {request.travel_days} 天规划基础信息采集，"
            "建议优先确认景点开放时间与酒店可订状态。"
        )
