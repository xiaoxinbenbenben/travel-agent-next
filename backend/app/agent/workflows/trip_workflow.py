"""Trip 工作流（占位）。"""

from __future__ import annotations

from app.agent.contracts import AgentRunResult
from app.agent.prompts import TRIP_SYSTEM_PROMPT, TRIP_USER_PROMPT_TEMPLATE
from app.agent.runtime import MiniAgent
from app.schemas.trip import TripRequest


class TripWorkflow:
    """Trip 编排入口。后续将接入多 Agent 与 MCP 工具。"""

    def __init__(self, agent: MiniAgent) -> None:
        self.agent = agent

    async def run(self, request: TripRequest) -> AgentRunResult:
        user_prompt = TRIP_USER_PROMPT_TEMPLATE.format(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            travel_days=request.travel_days,
            transportation=request.transportation,
            accommodation=request.accommodation,
            preferences=", ".join(request.preferences) if request.preferences else "无",
            free_text_input=request.free_text_input or "无",
        )
        return await self.agent.run(
            [
                {"role": "system", "content": TRIP_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )

