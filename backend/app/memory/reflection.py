from __future__ import annotations
from app.models.memory import Memory


class Reflector:
    """周期性反思：当记忆积累到阈值 + 到了间隔，用 LLM 生成高层洞察。"""

    def __init__(self, llm, interval: int = 5, min_memories: int = 5):
        self.llm = llm
        self.interval = interval
        self.min_memories = min_memories

    def should_reflect(self, current_tick: int, memory_count: int) -> bool:
        if memory_count < self.min_memories:
            return False
        return current_tick > 0 and current_tick % self.interval == 0

    async def reflect(self, memories: list[Memory], character_name: str, current_tick: int) -> Memory | None:
        if not self.should_reflect(current_tick, len(memories)):
            return None
        mem_text = "\n".join(f"- {m.content}" for m in memories[-10:])
        messages = [
            {"role": "system", "content": f"你是角色「{character_name}」的内心。回顾最近的记忆，生成一条高层反思/洞察。一句话。"},
            {"role": "user", "content": f"记忆：\n{mem_text}"},
        ]
        try:
            insight = await self.llm.complete(messages=messages)
        except Exception:
            return None
        return Memory(
            character_id=character_name,
            world_id=memories[0].world_id if memories else "",
            type="reflection",
            content=insight.strip(),
            tick=current_tick,
            importance=8.5,
        )
