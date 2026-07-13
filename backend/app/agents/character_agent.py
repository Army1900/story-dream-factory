from __future__ import annotations
import json
from app.agents.proposal import ActionProposal
from app.models.character import Character


class CharacterAgent:
    """角色 Agent：感知世界 → 检索记忆 → 规划 → 产出 ActionProposal。"""

    def __init__(self, character: Character, llm_gateway, memories: list[dict] | None = None):
        self.character = character
        self.llm = llm_gateway
        self.memories = memories or []

    def perceive(self, world_snapshot: dict) -> str:
        """从世界快照提取角色能感知的，返回文本。"""
        parts = []
        loc = world_snapshot.get("location", "未知")
        parts.append(f"你在{loc}。")
        present = world_snapshot.get("present", [])
        if present:
            others = [p for p in present if p != self.character.name]
            if others:
                parts.append(f"在场：{'、'.join(others)}。")
        events = world_snapshot.get("recent_events", [])
        if events:
            parts.append(f"近期事件：{'; '.join(events[-3:])}")
        state = self.character.state or {}
        if state.get("mood"):
            parts.append(f"你的心情：{state['mood']}。")
        return " ".join(parts)

    def _build_decision_prompt(self, perception: str) -> list[dict]:
        c = self.character
        personality = c.personality or {}
        goals = c.goals or {}
        backstory = c.backstory or ""
        mem_text = "\n".join(f"- {m.get('content','')}" for m in self.memories[-5:]) if self.memories else "（无记忆）"

        system = (
            f"你是角色「{c.name}」的大脑。根据你的性格、目标和记忆，决定此刻做什么。\n"
            f"性格：{json.dumps(personality, ensure_ascii=False)}\n"
            f"背景：{backstory}\n"
            f"目标：{json.dumps(goals, ensure_ascii=False)}\n"
            f"记忆：\n{mem_text}\n\n"
            f"输出 JSON：{{\"intent\":\"意图\",\"action_type\":\"action|dialogue|conflict|move|wait\","
            f"\"target\":\"目标\",\"expectation\":\"预期\",\"dialogue\":\"对白或空\"}}"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": perception},
        ]

    async def decide(self, world_snapshot: dict) -> ActionProposal:
        """感知→规划→产出 ActionProposal。"""
        perception = self.perceive(world_snapshot)
        messages = self._build_decision_prompt(perception)
        try:
            data = await self.llm.complete_json(messages=messages)
            return ActionProposal.from_dict(data)
        except Exception:
            return ActionProposal(intent="等待", action_type="wait")
