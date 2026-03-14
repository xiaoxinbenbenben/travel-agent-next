"""Trip specialist agents."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.contracts import AgentRunResult, LLMClientProtocol
from app.agent.prompts import (
    ATTRACTION_SYSTEM_PROMPT,
    ATTRACTION_USER_PROMPT_TEMPLATE,
    HOTEL_SYSTEM_PROMPT,
    HOTEL_USER_PROMPT_TEMPLATE,
    MEAL_SYSTEM_PROMPT,
    MEAL_USER_PROMPT_TEMPLATE,
    PLANNER_SYSTEM_PROMPT,
    PLANNER_USER_PROMPT_TEMPLATE,
    WEATHER_SYSTEM_PROMPT,
    WEATHER_USER_PROMPT_TEMPLATE,
)
from app.agent.runtime import MiniAgent
from app.agent.tool_registry import ToolRegistry


def _build_subset_registry(base_registry: ToolRegistry, allowed_tools: tuple[str, ...]) -> ToolRegistry:
    registry = ToolRegistry()
    tool_definitions = base_registry.list_tools()

    for tool_name in allowed_tools:
        definition = tool_definitions.get(tool_name)
        if definition is None:
            continue
        registry.register(
            tool_name,
            definition.handler,
            args_model=definition.args_model,
            description=definition.description,
        )

    return registry


class _SpecialistAgent:
    """Specialist agent 基类，封装固定 system prompt。"""

    def __init__(
        self,
        *,
        name: str,
        system_prompt: str,
        llm_client: LLMClientProtocol,
        tool_registry: ToolRegistry,
        max_steps: int = 6,
    ) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.tool_registry = tool_registry
        self._runtime = MiniAgent(
            name=name,
            llm_client=llm_client,
            tool_registry=tool_registry,
            max_steps=max_steps,
        )

    async def _run(self, user_prompt: str) -> AgentRunResult:
        return await self._runtime.run(
            [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )


class AttractionSearchAgent(_SpecialistAgent):
    def __init__(self, *, llm_client: LLMClientProtocol, tool_registry: ToolRegistry, max_steps: int = 6) -> None:
        super().__init__(
            name="AttractionSearchAgent",
            system_prompt=ATTRACTION_SYSTEM_PROMPT,
            llm_client=llm_client,
            tool_registry=tool_registry,
            max_steps=max_steps,
        )

    async def search(self, city: str, preference: str) -> AgentRunResult:
        return await self._run(
            ATTRACTION_USER_PROMPT_TEMPLATE.format(city=city, preferences=preference)
        )


class WeatherQueryAgent(_SpecialistAgent):
    def __init__(self, *, llm_client: LLMClientProtocol, tool_registry: ToolRegistry, max_steps: int = 6) -> None:
        super().__init__(
            name="WeatherQueryAgent",
            system_prompt=WEATHER_SYSTEM_PROMPT,
            llm_client=llm_client,
            tool_registry=tool_registry,
            max_steps=max_steps,
        )

    async def query(self, city: str) -> AgentRunResult:
        return await self._run(WEATHER_USER_PROMPT_TEMPLATE.format(city=city))


class HotelAgent(_SpecialistAgent):
    def __init__(self, *, llm_client: LLMClientProtocol, tool_registry: ToolRegistry, max_steps: int = 6) -> None:
        super().__init__(
            name="HotelAgent",
            system_prompt=HOTEL_SYSTEM_PROMPT,
            llm_client=llm_client,
            tool_registry=tool_registry,
            max_steps=max_steps,
        )

    async def search(self, city: str, accommodation: str) -> AgentRunResult:
        return await self._run(
            HOTEL_USER_PROMPT_TEMPLATE.format(city=city, accommodation=accommodation)
        )


class MealAgent(_SpecialistAgent):
    def __init__(self, *, llm_client: LLMClientProtocol, tool_registry: ToolRegistry, max_steps: int = 6) -> None:
        super().__init__(
            name="MealAgent",
            system_prompt=MEAL_SYSTEM_PROMPT,
            llm_client=llm_client,
            tool_registry=tool_registry,
            max_steps=max_steps,
        )

    async def search(self, city: str) -> AgentRunResult:
        return await self._run(MEAL_USER_PROMPT_TEMPLATE.format(city=city))


class PlannerAgent(_SpecialistAgent):
    def __init__(self, *, llm_client: LLMClientProtocol, tool_registry: ToolRegistry, max_steps: int = 6) -> None:
        super().__init__(
            name="PlannerAgent",
            system_prompt=PLANNER_SYSTEM_PROMPT,
            llm_client=llm_client,
            tool_registry=tool_registry,
            max_steps=max_steps,
        )

    async def plan(self, planner_context: str) -> AgentRunResult:
        return await self._run(
            PLANNER_USER_PROMPT_TEMPLATE.format(planner_context=planner_context)
        )


@dataclass(frozen=True)
class TripSpecialists:
    attraction_agent: AttractionSearchAgent
    weather_agent: WeatherQueryAgent
    hotel_agent: HotelAgent
    meal_agent: MealAgent
    planner_agent: PlannerAgent


def build_trip_specialists(
    *,
    llm_client: LLMClientProtocol,
    base_tool_registry: ToolRegistry,
    max_steps: int = 6,
) -> TripSpecialists:
    return TripSpecialists(
        attraction_agent=AttractionSearchAgent(
            llm_client=llm_client,
            tool_registry=_build_subset_registry(base_tool_registry, ("search_poi",)),
            max_steps=max_steps,
        ),
        weather_agent=WeatherQueryAgent(
            llm_client=llm_client,
            tool_registry=_build_subset_registry(base_tool_registry, ("get_weather",)),
            max_steps=max_steps,
        ),
        hotel_agent=HotelAgent(
            llm_client=llm_client,
            tool_registry=_build_subset_registry(base_tool_registry, ("search_poi",)),
            max_steps=max_steps,
        ),
        meal_agent=MealAgent(
            llm_client=llm_client,
            tool_registry=_build_subset_registry(base_tool_registry, ("search_poi",)),
            max_steps=max_steps,
        ),
        planner_agent=PlannerAgent(
            llm_client=llm_client,
            tool_registry=ToolRegistry(),
            max_steps=max_steps,
        ),
    )
