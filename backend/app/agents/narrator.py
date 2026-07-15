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
            if not narration or not narration.strip():
                narration = self._fallback(proposal)
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

    async def narrate_group(
        self,
        proposals: list[ActionProposal],
        participants: list[str],
        world_name: str = "",
        location: str = "",
        world_setting: str = "",
    ) -> str:
        """把同地点多角色的行动合并成一段连贯的文学叙述。"""
        messages = self._build_group_prompt(proposals, participants, world_name, location, world_setting)
        try:
            narration = await self.llm.complete(messages=messages)
            if narration and narration.strip():
                return narration
        except Exception:
            pass
        return self._group_fallback(proposals)

    def _build_prompt(self, proposal: ActionProposal, world_name: str, loc: str, setting: str) -> list[dict]:
        system = (
            f"你是世界「{world_name}」的意识，一位文学大师。\n"
            f"世界观：{setting}\n\n"
            f"你的任务是：用 3-5 句优美的文学语言，叙述此刻发生的事。\n"
            f"要求：\n"
            f"- 第三人称全知视角\n"
            f"- 先交代场景（1句），再叙述行动（1-2句），再写角色状态/情绪（1句）\n"
            f"- 不要重复用户已知的信息\n"
            f"- 有画面感，有节奏\n"
            f"- 不要用「角色说出了心中的话」这种模板\n"
        )
        detail = (
            f"地点：{loc}\n"
            f"角色意图：{proposal.intent}\n"
            f"行动类型：{proposal.action_type}\n"
        )
        if proposal.target:
            detail += f"目标：{proposal.target}\n"
        if proposal.dialogue:
            detail += f"对白：「{proposal.dialogue}」\n（把对白融入叙述，不要单独列出）\n"
        return [{"role": "system", "content": system}, {"role": "user", "content": detail}]

    def _build_group_prompt(
        self,
        proposals: list[ActionProposal],
        participants: list[str],
        world_name: str,
        loc: str,
        setting: str,
    ) -> list[dict]:
        """合并同地点多角色行动的叙述 prompt：交织成一段场景。"""
        system = (
            f"你是世界「{world_name}」的意识，一位文学大师。\n"
            f"世界观：{setting}\n\n"
            f"同一地点「{loc}」里，多位角色正同时行动。"
            f"用 4-7 句优美的文学语言，把他们的行动交织成一段连贯的场景叙述。\n"
            f"要求：\n"
            f"- 第三人称全知视角，像小说的一个段落\n"
            f"- 先用 1 句交代场景氛围\n"
            f"- 再依次（或交织）叙述各角色的行动与对话，角色之间要有互动/张力\n"
            f"- 把对话自然融入叙述，不要单独罗列\n"
            f"- 结尾用 1 句点出此刻的情绪或悬念\n"
            f"- 有画面感，有节奏，不要用模板化套话\n"
        )
        lines = [f"地点：{loc}", f"在场角色：{'、'.join(participants)}", "此刻各角色行动："]
        for name, p in zip(participants, proposals):
            line = f"- {name}（{p.action_type}）：意图「{p.intent}」"
            if p.target:
                line += f"，对象 {p.target}"
            if p.dialogue:
                line += f"，对白「{p.dialogue}」"
            lines.append(line)
        return [{"role": "system", "content": system}, {"role": "user", "content": "\n".join(lines)}]

    def _map_type(self, action_type: str) -> EventType:
        mapping = {
            "dialogue": EventType.dialogue,
            "conflict": EventType.conflict,
            "cooperation": EventType.relationship_change,
            "investigate": EventType.action,
            "interact": EventType.action,
            "move": EventType.action,
            "wait": EventType.action,
            "action": EventType.action,
        }
        return mapping.get(action_type, EventType.action)

    def _fallback(self, proposal: ActionProposal) -> str:
        """LLM 失败时的降级叙述（不再用模板包装对白）。"""
        if proposal.dialogue:
            return proposal.dialogue  # 直接返回对白，不加模板包装
        if proposal.action_type == "wait":
            return "时间在这一刻凝固。"
        return f"{proposal.intent}。"

    def _group_fallback(self, proposals: list[ActionProposal]) -> str:
        """多角色合并叙述的降级：把各角色的对白/意图连成一段。"""
        parts: list[str] = []
        for p in proposals:
            if p.dialogue:
                parts.append(p.dialogue)
            elif p.action_type == "wait":
                parts.append("沉默")
            elif p.intent:
                parts.append(p.intent)
        return "　".join(parts) if parts else "场面一度安静。"
