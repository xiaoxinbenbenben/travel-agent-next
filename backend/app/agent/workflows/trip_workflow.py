"""Trip 工作流编排。"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import json
import logging
from typing import Any, Dict, List, Protocol

from app.agent.contracts import AgentRunResult, ToolTrace
from app.core import log_duration
from app.schemas.trip import TripRequest

logger = logging.getLogger(__name__)


class _FallbackCapableAgent(Protocol):
    name: str
    tool_registry: Any


class TripWorkflow:
    """Trip 编排入口：前置采集 + 最终 planner。"""

    def __init__(
        self,
        attraction_agent: Any,
        weather_agent: Any,
        hotel_agent: Any,
        meal_agent: Any,
        planner_agent: Any,
    ) -> None:
        self.attraction_agent = attraction_agent
        self.weather_agent = weather_agent
        self.hotel_agent = hotel_agent
        self.meal_agent = meal_agent
        self.planner_agent = planner_agent

    async def run(self, request: TripRequest) -> AgentRunResult:
        all_traces: List[ToolTrace] = []
        with log_duration(
            logger,
            "TripWorkflow",
            start_message="🚀 开始 TripWorkflow 编排...",
            success_message="✅ TripWorkflow 完成",
        ):
            preplanner_stages = await asyncio.gather(
                *self._build_preplanner_tasks(request)
            )
            for stage in preplanner_stages:
                all_traces.extend(stage.traces)

            with log_duration(
                logger,
                "步骤5: 生成行程计划",
                start_message="📋 步骤5: 生成行程计划...",
            ):
                planner_stage = await self.planner_agent.plan(
                    self._planner_context(request, all_traces)
                )
            all_traces.extend(planner_stage.traces)
            return AgentRunResult(content=planner_stage.content, traces=all_traces)

    def _build_preplanner_tasks(self, request: TripRequest) -> List[Awaitable[AgentRunResult]]:
        tasks: List[Awaitable[AgentRunResult]] = []

        for preference in self._attraction_preferences(request):
            tasks.append(self._run_attraction_stage(request.city, preference))

        tasks.append(self._run_weather_stage(request.city))

        hotel_keyword = request.accommodation or "酒店"
        tasks.append(self._run_hotel_stage(request.city, hotel_keyword))
        tasks.append(self._run_meal_stage(request.city))
        return tasks

    async def _run_attraction_stage(self, city: str, preference: str) -> AgentRunResult:
        with log_duration(
            logger,
            f"步骤1: 搜索景点[{preference}]",
            start_message=f"📍 步骤1: 搜索景点 [{preference}]...",
        ):
            return await self._run_stage_with_fallback(
                agent=self.attraction_agent,
                runner=lambda: self.attraction_agent.search(city, preference),
                required_tool="search_poi",
                fallback_arguments={
                    "keywords": preference,
                    "city": city,
                    "citylimit": True,
                },
            )

    async def _run_weather_stage(self, city: str) -> AgentRunResult:
        with log_duration(
            logger,
            "步骤2: 查询天气",
            start_message="🌤️ 步骤2: 查询天气...",
        ):
            return await self._run_stage_with_fallback(
                agent=self.weather_agent,
                runner=lambda: self.weather_agent.query(city),
                required_tool="get_weather",
                fallback_arguments={"city": city},
            )

    async def _run_hotel_stage(self, city: str, hotel_keyword: str) -> AgentRunResult:
        with log_duration(
            logger,
            "步骤3: 搜索酒店",
            start_message="🏨 步骤3: 搜索酒店...",
        ):
            return await self._run_stage_with_fallback(
                agent=self.hotel_agent,
                runner=lambda: self.hotel_agent.search(city, hotel_keyword),
                required_tool="search_poi",
                fallback_arguments={
                    "keywords": hotel_keyword,
                    "city": city,
                    "citylimit": True,
                },
            )

    async def _run_meal_stage(self, city: str) -> AgentRunResult:
        with log_duration(
            logger,
            "步骤4: 搜索餐饮",
            start_message="🍽️ 步骤4: 搜索餐饮...",
        ):
            return await self._run_stage_with_fallback(
                agent=self.meal_agent,
                runner=lambda: self.meal_agent.search(city),
                required_tool="search_poi",
                fallback_arguments={
                    "keywords": "美食 餐厅",
                    "city": city,
                    "citylimit": True,
                },
            )

    async def _run_stage_with_fallback(
        self,
        *,
        agent: _FallbackCapableAgent,
        runner: Callable[[], Awaitable[AgentRunResult]],
        required_tool: str,
        fallback_arguments: Dict[str, Any],
    ) -> AgentRunResult:
        result = await runner()
        traces = list(result.traces)
        if any(item.tool_name == required_tool for item in traces):
            return AgentRunResult(content=result.content, traces=traces)

        fallback_result = await agent.tool_registry.dispatch(required_tool, fallback_arguments)
        traces.append(
            ToolTrace(
                agent_name=agent.name,
                tool_name=required_tool,
                arguments=fallback_arguments,
                result=fallback_result,
            )
        )
        return AgentRunResult(content=result.content, traces=traces)

    @staticmethod
    def _attraction_preferences(request: TripRequest) -> List[str]:
        preferences: List[str] = []
        for item in request.preferences:
            value = item.strip()
            if value and value not in preferences:
                preferences.append(value)
        return preferences or ["热门景点"]

    @staticmethod
    def _planner_context(request: TripRequest, traces: List[ToolTrace]) -> str:
        def _summarize_item(item: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "poi_id": str(item.get("id", "")),
                "name": str(item.get("name", "")),
                "address": str(item.get("address", "")),
                "category": str(item.get("type", item.get("typecode", ""))),
            }

        attraction_candidates: Dict[str, List[Dict[str, Any]]] = {}
        hotel_candidates: List[Dict[str, Any]] = []
        meal_candidates: List[Dict[str, Any]] = []
        weather_items: List[Dict[str, Any]] = []

        for trace in traces:
            if trace.tool_name == "get_weather" and isinstance(trace.result, list):
                weather_items = [
                    item
                    for item in trace.result
                    if isinstance(item, dict)
                ]
                continue

            if trace.tool_name != "search_poi" or not isinstance(trace.result, list):
                continue

            items = [_summarize_item(item) for item in trace.result if isinstance(item, dict)]
            keywords = str(trace.arguments.get("keywords", "")).strip() or "热门景点"
            if any(token in keywords for token in ("酒店", "宾馆", "民宿", "客栈", "青旅", "住宿")):
                hotel_candidates.extend(items)
            elif any(token in keywords for token in ("餐厅", "小吃", "早餐", "午餐", "晚餐", "饭店", "美食")):
                meal_candidates.extend(items)
            else:
                attraction_candidates.setdefault(keywords, []).extend(items)

        planner_payload = {
            "request": {
                "city": request.city,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "travel_days": request.travel_days,
                "transportation": request.transportation,
                "accommodation": request.accommodation,
                "preferences": request.preferences,
                "free_text_input": request.free_text_input or "",
            },
            "weather": weather_items,
            "attractions_by_theme": attraction_candidates,
            "hotel_candidates": hotel_candidates,
            "meal_candidates": meal_candidates,
        }
        return json.dumps(planner_payload, ensure_ascii=False)
