from __future__ import annotations
from app.agents.proposal import ActionProposal
from app.models.event import Event
from app.models.enums import EventType


class Narrator:
    """世界意识-叙述者：把 ActionProposal 转成文学叙述 Event。"""

    def __init__(self, llm_gateway):
        self.llm = llm_gateway

    async def narrate(
        self,
        proposal: ActionProposal,
        world_name: str = "",
        tick: int = 0,
        location: str = "",
        world_setting: str = "",
    ) -> Event:
        messages = self._build_prompt(proposal, world_name, location, world_setting)
        try:
            narration = await self.llm.complete(messages=messages)
        except Exception:
            narration = self._fallback(proposal)

        event_type = self._map_type(proposal.action_type)
        return Event(
            tick=tick,
            type=event_type,
            participants=[proposal.target] if proposal.target else [],
            location_id=location,
            payload=proposal.to_dict(),
            narration=narration,
        )

    def _build_prompt(self, proposal: ActionProposal, world: str, loc: str, setting: str) -> list[dict]:
        system = (
            f"你是世界「{world}」的意识，一位文学叙述者。\n"
            f"世界观：{setting}\n"
            f"用 2-3 句优美的文学语言，叙述此刻发生的事。\n"
            f"不要角色第一人称，用第三人称全知视角。"
        )
        detail = (
            f"地点：{loc}\n"
            f"角色意图：{proposal.intent}\n"
            f"行动类型：{proposal.action_type}\n"
            f"目标：{proposal.target}\n"
        )
        if proposal.dialogue:
            detail += f"对白：「{proposal.dialogue}」\n"
        return [{"role": "system", "content": system}, {"role": "user", "content": detail}]

    def _map_type(self, action_type: str) -> EventType:
        mapping = {
            "dialogue": EventType.dialogue,
            "conflict": EventType.conflict,
            "move": EventType.action,
            "wait": EventType.action,
            "action": EventType.action,
        }
        return mapping.get(action_type, EventType.action)

    def _fallback(self, proposal: ActionProposal) -> str:
        """LLM 失败时的降级叙述。"""
        if proposal.dialogue:
            return f"角色说出了心中的话：「{proposal.dialogue}」"
        if proposal.action_type == "wait":
            return "一切陷入静默，时间仿佛凝滞。"
        return f"{proposal.intent}——在这一刻发生了。"
