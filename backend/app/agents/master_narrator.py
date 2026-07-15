"""总叙述者：把一整拍所有角色行动写成一段连贯的小说节选。

替代旧的“逐角色 / 按地点分组”叙述方式。输入场景方向 + 各角色提案 +
物理裁决结果 + 故事状态，输出 200-500 字的中文小说节选（单一字符串），
强制内容比例（场景/行动/内心/旁白/留白），杜绝“游戏日志”式割裂描述。
"""

from __future__ import annotations

from typing import Any

from app.agents.proposal import ActionProposal


class MasterNarrator:
    """整拍小说化叙述者。"""

    def __init__(self, llm_gateway: Any):
        self.llm = llm_gateway

    async def narrate(
        self,
        scene_direction: dict,
        proposals: list[ActionProposal],
        resolved: list,
        world: dict,
        story_state: dict,
        tick: int,
        participants: list[str] | None = None,
    ) -> str:
        """写一段连贯的小说节选（200-500 字中文）。

        参数:
            scene_direction: :class:`~app.agents.scene_director.SceneDirector` 的输出。
            proposals: 本拍各角色行动提案（与 participants 对齐）。
            resolved: 物理引擎裁决结果（含 ``success`` / ``new_state``）。
            world: ``{"name","setting",...}``。
            story_state: ``{"narrative_summary","last_narration",...}``。
            tick: 当前 tick。
            participants: 各 proposal 对应的角色名（用于在叙述中点名）。

        返回:
            一段小说节选文本。LLM 失败时退化为基于提案的拼接叙述。
        """
        messages = self._build_prompt(
            scene_direction, proposals, resolved, world, story_state, tick, participants
        )
        try:
            narration = await self.llm.complete(messages=messages)
            if not narration or not narration.strip():
                narration = self._fallback(proposals)
        except Exception:
            narration = self._fallback(proposals)
        return narration

    # ----------------------------------------------------------------- prompt
    def _build_prompt(
        self,
        scene_direction: dict,
        proposals: list[ActionProposal],
        resolved: list,
        world: dict,
        story_state: dict,
        tick: int,
        participants: list[str] | None,
    ) -> list[dict]:
        world_name = world.get("name", "（未命名）")
        setting = world.get("setting", "")
        scene_text = self._format_scene(scene_direction)
        actions_text = self._format_actions(proposals, resolved, participants)
        last_ending = story_state.get("last_narration", "") or "（故事开头，无需衔接）"
        summary = story_state.get("narrative_summary", "") or "（尚无摘要）"
        non_char = scene_direction.get("non_character_events", []) if scene_direction else []
        non_char_text = "；".join(non_char) if non_char else "（无）"

        system = (
            "你是一位畅销奇幻小说大师，正在写下一幕。\n\n"
            "【创作要求——严格遵守】\n"
            "内容比例：\n"
            "- 场景与环境描写 25-30%（天气/地点/氛围/感官细节——让读者“看到”画面）\n"
            "- 角色行动与对话 25-30%（自然融入叙述，不要用“XX说”简单格式，"
            "用动作带出对话）\n"
            "- 角色内心活动 15-20%（犹豫/回忆/恐惧——通过细节暗示，"
            "不要写“他感到愤怒”）\n"
            "- 世界与旁白 10-15%（环境变化/其他人反应/主题评论/戏剧讽刺）\n"
            "- 留白与节奏 5-10%（沉默/停顿/时间流逝）\n\n"
            "写作手法：\n"
            "- 展现而非告知：写“他握杯子的手指压白了关节”，不要写“他很紧张”\n"
            "- 感官层次：视觉+听觉+触觉+嗅觉（酒馆的麦酒味、炭火温度、木门嘎吱声）\n"
            "- 角色声音不同：凯尔优雅从容 vs 艾伦直接粗粝 vs 贝拉颤抖隐忍\n"
            "- 节奏：紧张用短句；过渡用长句；安静时留白\n\n"
            "绝对禁止：\n"
            "- “角色说出了心中的话”模板\n"
            "- “（动作描写）”括号格式\n"
            "- 把每个角色单独成段\n"
            "- 对话超过 30%\n"
        )
        user = (
            f"世界：{world_name}，{setting}\n"
            f"场景意图：{scene_text}\n"
            f"角色行动（这一拍各角色做了什么）：\n{actions_text}\n\n"
            f"上一幕结尾（需要衔接）：{last_ending}\n"
            f"故事摘要：{summary}\n"
            f"非角色事件（环境/世界）：{non_char_text}\n\n"
            "【输出】\n"
            "直接写小说节选（200-500 字中文），不要加任何注释或说明。"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    # ----------------------------------------------------------- 格式化辅助
    @staticmethod
    def _format_scene(scene_direction: dict) -> str:
        if not scene_direction:
            return "（无明确方向，自由发挥）"
        parts = []
        if scene_direction.get("scene_type"):
            parts.append(f"类型 {scene_direction['scene_type']}")
        if scene_direction.get("atmosphere"):
            parts.append(f"氛围 {scene_direction['atmosphere']}")
        if scene_direction.get("dramatic_intent"):
            parts.append(f"意图 {scene_direction['dramatic_intent']}")
        if scene_direction.get("pacing"):
            parts.append(f"节奏 {scene_direction['pacing']}")
        focus = scene_direction.get("focus_characters", [])
        if focus:
            parts.append("聚焦 " + "、".join(focus))
        return "；".join(parts) if parts else "（自由发挥）"

    @staticmethod
    def _format_actions(
        proposals: list[ActionProposal],
        resolved: list,
        participants: list[str] | None,
    ) -> str:
        if not proposals:
            return "（本拍无角色行动）"
        names = participants or [f"角色{i+1}" for i in range(len(proposals))]
        lines = []
        for i, p in enumerate(proposals):
            name = names[i] if i < len(names) else f"角色{i+1}"
            seg = f"- {name}（{p.action_type}）：{p.intent or '（无明确意图）'}"
            if p.target:
                seg += f"｜对象：{p.target}"
            if p.dialogue:
                seg += f"｜对白：「{p.dialogue}」"
            # 裁决结果（成功/失败）
            if i < len(resolved):
                r = resolved[i]
                ok = getattr(r, "success", None)
                if ok is True:
                    seg += "｜结果：成功"
                elif ok is False:
                    seg += "｜结果：受挫"
            lines.append(seg)
        return "\n".join(lines)

    @staticmethod
    def _fallback(proposals: list[ActionProposal]) -> str:
        """LLM 失败时的降级叙述：把对白/意图连成一段。"""
        parts: list[str] = []
        for p in proposals:
            if p.dialogue:
                parts.append(p.dialogue)
            elif p.intent:
                parts.append(p.intent)
        return "　".join(parts) if parts else "场面一度安静。"
