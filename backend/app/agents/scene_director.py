"""场景导演：每个 tick 开头决定这一拍的戏剧方向。

在角色行动之前，结合世界设定、故事摘要、未解悬念、角色状态，输出一段
YAML 描述：场景类型 / 氛围 / 戏剧意图 / 节奏 / 镜头聚焦 / 非角色事件。
输出供 :class:`~app.agents.master_narrator.MasterNarrator` 与角色 Agent 共用。
"""

from __future__ import annotations

from typing import Any

import yaml


class SceneDirector:
    """每一拍的戏剧方向决策者。"""

    def __init__(self, llm_gateway: Any):
        self.llm = llm_gateway

    async def direct(
        self,
        world_state: dict,
        story_state: dict,
        tick: int,
        character_states: list[dict],
    ) -> dict:
        """决定这一拍的戏剧方向。

        参数:
            world_state: ``{"name", "setting", "rules", ...}``
            story_state: ``{"phase", "narrative_summary", "last_narration",
                            "open_threads", "dramatic_tensions", ...}``
            tick: 当前 tick。
            character_states: ``[{"name","location","mood","goal"}, ...]``

        返回:
            规范化后的 dict：
            ``{scene_type, atmosphere, dramatic_intent, pacing,
               focus_characters, non_character_events}``
        """
        messages = self._build_prompt(world_state, story_state, tick, character_states)
        try:
            raw = await self.llm.complete(messages=messages)
            parsed = yaml.safe_load(raw) if raw else None
            if not isinstance(parsed, dict):
                parsed = {}
        except Exception:
            parsed = {}
        return self._normalize(parsed)

    # ----------------------------------------------------------------- prompt
    def _build_prompt(
        self,
        world_state: dict,
        story_state: dict,
        tick: int,
        character_states: list[dict],
    ) -> list[dict]:
        world_name = world_state.get("name", "（未命名）")
        setting = world_state.get("setting", "（无）")
        phase = story_state.get("phase", "setup") or "setup"
        last_narration = story_state.get("last_narration", "") or "（开头）"
        narrative_summary = story_state.get("narrative_summary", "") or "（故事刚开始）"
        open_threads = self._format_threads(story_state.get("open_threads", []))
        tensions = self._format_tensions(story_state.get("dramatic_tensions", []))
        char_block = self._format_characters(character_states)

        system = (
            "你是故事梦工厂的“场景导演”。你的职责是：在角色行动之前，"
            "决定这一拍的戏剧方向，让叙事具备起承转合与画面感。"
            "严格只输出一个 YAML 对象，不要 markdown 代码块，不要解释。"
        )
        user = (
            f"世界：{world_name}\n"
            f"世界设定：{setting}\n"
            f"当前阶段：{phase}（setup/rising_action/climax/falling_action）\n"
            f"Tick：{tick}\n\n"
            f"上一拍叙述结尾：{last_narration}\n"
            f"故事摘要：{narrative_summary}\n"
            f"未解悬念：{open_threads}\n"
            f"当前张力：{tensions}\n\n"
            f"角色状态：\n{char_block}\n\n"
            "请输出 YAML（字段如下）：\n"
            "scene_type: （这一拍的类型：对峙|过渡|揭露|高潮|反思|日常）\n"
            "atmosphere: （场景氛围，2-3 句，含感官细节）\n"
            "dramatic_intent: （这一拍要推进什么）\n"
            "pacing: slow|medium|fast\n"
            "focus_characters: [镜头聚焦的角色名]\n"
            "non_character_events: [非角色事件——天气变化/远处声音/其他人的生活/"
            "自然现象/世界在发生的事]"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    # ------------------------------------------------------------ 标准化输出
    def _normalize(self, d: dict) -> dict:
        """把 LLM 返回（可能缺字段/类型错）规范化为稳定结构。"""
        return {
            "scene_type": self._str(d.get("scene_type")) or "日常",
            "atmosphere": self._str(d.get("atmosphere")),
            "dramatic_intent": self._str(d.get("dramatic_intent")),
            "pacing": self._str(d.get("pacing")) or "medium",
            "focus_characters": self._as_list(d.get("focus_characters")),
            "non_character_events": self._as_list(d.get("non_character_events")),
        }

    @staticmethod
    def _str(v) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @staticmethod
    def _as_list(v) -> list:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v if x is not None]
        # 单个标量也容错成列表
        s = str(v).strip()
        return [s] if s else []

    # ----------------------------------------------------------- 格式化辅助
    @staticmethod
    def _format_threads(threads) -> str:
        if not threads:
            return "（无）"
        lines = []
        for t in threads:
            if isinstance(t, dict):
                desc = t.get("description", "")
                inten = t.get("intensity", "")
                lines.append(f"- {desc}（强度 {inten}）" if inten else f"- {desc}")
            else:
                lines.append(f"- {t}")
        return "\n".join(lines)

    @staticmethod
    def _format_tensions(tensions) -> str:
        if not tensions:
            return "（无）"
        lines = []
        for t in tensions:
            if isinstance(t, dict):
                between = t.get("between", [])
                if isinstance(between, list):
                    between = "、".join(str(x) for x in between)
                ttype = t.get("type", "")
                inten = t.get("intensity", "")
                lines.append(f"- {between}（{ttype}，强度 {inten}）")
            else:
                lines.append(f"- {t}")
        return "\n".join(lines)

    @staticmethod
    def _format_characters(character_states: list[dict]) -> str:
        if not character_states:
            return "（无角色）"
        lines = []
        for c in character_states:
            name = c.get("name", "?")
            loc = c.get("location", "未知")
            mood = c.get("mood", "")
            goal = c.get("goal", "")
            line = f"- {name} @ {loc}"
            if mood:
                line += f"，心情：{mood}"
            if goal:
                line += f"，目标：{goal}"
            lines.append(line)
        return "\n".join(lines)
