"""戏剧状态管理：跟踪叙事弧、悬念、张力、摘要。

每个世界目录下一份 ``story_state.yaml``，由 :class:`StoryStateManager`
读写。``world_dir=None`` 时退化为内存对象（不落盘），便于测试。
"""

from __future__ import annotations

import re
from typing import Any

from app.persistence.world_store import WorldStore


# 每隔多少 tick 用 LLM 压缩一次叙事摘要
_SUMMARY_INTERVAL = 3
# 保留多少条近期叙述供摘要参考
_NARRATION_WINDOW = 6
# last_narration 保留的尾句数
_TAIL_SENTENCES = 3

_SENTENCE_SPLIT = re.compile(r"(?<=[。！？…])")


class StoryStateManager:
    """加载/保存/更新一个世界的戏剧状态。"""

    def __init__(self, world_dir: str | None = None):
        self.world_dir = world_dir
        self._store = WorldStore()

    # ------------------------------------------------------------------- I/O
    def load(self) -> dict:
        """从 ``story_state.yaml`` 加载；不存在或无 world_dir 返回初始状态。"""
        if not self.world_dir:
            return self.initial_state()
        data = self._store.load_story_state(self.world_dir)
        if not isinstance(data, dict):
            return self.initial_state()
        # 合并默认键，避免老文件缺字段
        merged = self.initial_state()
        merged.update(data)
        return merged

    def save(self, state: dict) -> None:
        """保存到 ``story_state.yaml``；无 world_dir 时为空操作。"""
        if not self.world_dir:
            return
        self._store.save_story_state(self.world_dir, state)

    def initial_state(self) -> dict:
        """返回初始戏剧状态。"""
        return {
            "act": 1,
            "phase": "setup",
            "narrative_summary": "",
            "last_narration": "",
            "open_threads": [],
            "dramatic_tensions": [],
            "recent_narrations": [],
        }

    # --------------------------------------------------------------- 更新逻辑
    async def update_after_tick(
        self,
        state: dict,
        narration: str,
        tick: int,
        llm: Any,
    ) -> dict:
        """每 tick 后更新：滚动近期叙述、保存结尾衔接句、定期压缩摘要。

        - ``last_narration``：保存叙述最后 2-3 句，供下一 tick 衔接。
        - ``recent_narrations``：保留最近若干条叙述（内部辅助字段）。
        - ``narrative_summary``：每 ``_SUMMARY_INTERVAL`` tick 用 LLM 压缩成
          2-3 句摘要。LLM 失败时保留旧摘要，不阻塞 tick。
        """
        # 1. 滚动近期叙述窗口
        recent = list(state.get("recent_narrations", []))
        if narration:
            recent.append(narration)
        recent = recent[-_NARRATION_WINDOW:]
        state["recent_narrations"] = recent

        # 2. 结尾衔接句
        state["last_narration"] = self._tail(narration)

        # 3. 定期压缩摘要
        if (tick + 1) % _SUMMARY_INTERVAL == 0 and recent:
            try:
                summarized = await self._summarize(
                    llm,
                    state.get("narrative_summary", ""),
                    recent,
                )
                if summarized:
                    state["narrative_summary"] = summarized
            except Exception:
                # 摘要失败不阻塞主流程
                pass

        self.save(state)
        return state

    # --------------------------------------------------------------- 辅助方法
    @staticmethod
    def _tail(narration: str, max_sentences: int = _TAIL_SENTENCES) -> str:
        """取叙述的末尾若干句（按中文句末标点切分）。"""
        if not narration or not narration.strip():
            return ""
        parts = _SENTENCE_SPLIT.split(narration)
        parts = [p.strip() for p in parts if p and p.strip()]
        if not parts:
            return narration.strip()
        return "".join(parts[-max_sentences:])

    @staticmethod
    async def _summarize(llm: Any, existing_summary: str, recent_narrations: list[str]) -> str:
        """用 LLM 把已有摘要 + 最近叙述压缩成 2-3 句中文摘要。"""
        joined = " / ".join(recent_narrations[-_SUMMARY_INTERVAL:])
        system = (
            "你是故事编辑。把给定的故事片段压缩成 2-3 句中文摘要，"
            "保留关键事件、人物关系变化与未解悬念。只输出摘要本身，"
            "不要加前缀、不要解释。"
        )
        user = (
            f"已有摘要：{existing_summary or '（无）'}\n"
            f"最新片段：{joined}\n"
            f"请输出更新后的 2-3 句摘要。"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        out = await llm.complete(messages=messages)
        if not out or not out.strip():
            return existing_summary
        return out.strip()
