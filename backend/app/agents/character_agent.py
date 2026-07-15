from __future__ import annotations
import json
from app.agents.proposal import ActionProposal
from app.models.character import Character
from app.memory.retrieval import MemoryRetriever


class CharacterAgent:
    """角色 Agent：感知世界 → 检索记忆 → 规划 → 产出 ActionProposal。"""

    def __init__(self, character: Character, llm_gateway, memories: list[dict] | None = None):
        self.character = character
        self.llm = llm_gateway
        self.memories = memories or []
        self.retriever = MemoryRetriever()

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

    def _build_decision_prompt(
        self,
        perception: str,
        current_tick: int = 0,
        scene_context: dict | None = None,
        narrative_summary: str = "",
    ) -> list[dict]:
        c = self.character
        personality = c.personality or {}
        goals = c.goals or {}
        backstory = c.backstory or ""
        # 检索相关记忆（top 5）
        retrieved = self.retriever.retrieve(self.memories, query_vec=[], current_tick=current_tick, top_k=5)
        mem_text = "\n".join(f"- {self._mem_content(m)}" for m in retrieved) if retrieved else "（无记忆）"

        # 场景方向与叙事摘要（由 SceneDirector / StoryStateManager 提供，可选）
        scene_block = self._format_scene_context(scene_context)
        summary_block = (
            f"故事到目前为止：{narrative_summary}\n" if narrative_summary else ""
        )

        system = (
            f"你是角色「{c.name}」的大脑。根据你的性格、目标、记忆和当前处境，决定此刻做什么。\n"
            f"性格：{json.dumps(personality, ensure_ascii=False)}\n"
            f"背景：{backstory}\n"
            f"目标：{json.dumps(goals, ensure_ascii=False)}\n"
            f"记忆：\n{mem_text}\n\n"
            f"{summary_block}"
            f"{scene_block}"
            f"可选行动类型（action_type 字段，选最贴切的一个）：\n"
            f"- dialogue：与在场角色交谈（需填 target 为对方角色名，dialogue 填对白原文）\n"
            f"- conflict：与目标发生冲突/对抗（需填 target）\n"
            f"- cooperation：与目标合作/协助（需填 target）\n"
            f"- investigate：调查、探索、搜寻线索（target 可为物件/地点/谜题）\n"
            f"- interact：与物件或环境互动（如开门、取物、翻阅）\n"
            f"- move：前往其他地点（target 填目的地）\n"
            f"- action：执行其他通用行动\n"
            f"- wait：按兵不动，观察等待\n\n"
            f"决策要点：\n"
            f"- 留意在场其他角色的状态、情绪与可能反应，你的行动会影响他们\n"
            f"- 行动应推进你的目标，且符合你的性格与背景\n"
            f"- 优先选择有戏剧张力、能推动剧情发展的行动，避免无意义的 wait\n"
            f"- 如果给定了“这一拍的戏剧方向”，尽量让你的行动贴合该方向\n\n"
            f"严格只输出一个 JSON 对象（不要 markdown、不要解释、不要代码块），字段如下：\n"
            f'{{"intent":"一句话描述你的意图","action_type":"dialogue|conflict|cooperation|investigate|interact|move|action|wait",'
            f'"target":"行动对象（角色名/地点/物件；无关则空字符串）","expectation":"你期望达到的结果","dialogue":"仅当 action_type=dialogue 时填对白内容，否则空字符串"}}'
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": perception},
        ]

    @staticmethod
    def _format_scene_context(scene_context: dict | None) -> str:
        """把 SceneDirector 的输出格式化为角色可读的戏剧方向提示。"""
        if not scene_context:
            return ""
        parts = []
        if scene_context.get("scene_type"):
            parts.append(f"本拍类型：{scene_context['scene_type']}")
        if scene_context.get("dramatic_intent"):
            parts.append(f"戏剧方向：{scene_context['dramatic_intent']}")
        if scene_context.get("atmosphere"):
            parts.append(f"氛围：{scene_context['atmosphere']}")
        focus = scene_context.get("focus_characters", [])
        if focus:
            parts.append("镜头聚焦：" + "、".join(focus))
        if not parts:
            return ""
        return "【这一拍的戏剧方向】" + "；".join(parts) + "\n"

    @staticmethod
    def _mem_content(m) -> str:
        """从记忆项读取内容，兼容 Memory 对象与 dict。"""
        if isinstance(m, dict):
            return m.get("content", "")
        return getattr(m, "content", "") or ""

    async def decide(
        self,
        world_snapshot: dict,
        current_tick: int = 0,
        scene_context: dict | None = None,
        narrative_summary: str = "",
    ) -> ActionProposal:
        """感知→规划→产出 ActionProposal。

        参数:
            world_snapshot: 世界快照（地点/在场/近期事件）。
            current_tick: 当前 tick。
            scene_context: 可选，本拍戏剧方向（来自 SceneDirector）。
            narrative_summary: 可选，故事摘要（来自 StoryStateManager）。
        """
        perception = self.perceive(world_snapshot)
        messages = self._build_decision_prompt(
            perception,
            current_tick=current_tick,
            scene_context=scene_context,
            narrative_summary=narrative_summary,
        )
        try:
            data = await self.llm.complete_json(messages=messages)
            return ActionProposal.from_dict(data)
        except Exception:
            return ActionProposal(intent="等待", action_type="wait")
