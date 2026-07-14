from __future__ import annotations
from app.models.event import Event
from app.models.memory import Memory
from app.models.enums import EventType

_IMPORTANCE_MAP = {
    EventType.conflict: 9.0,
    EventType.inciting: 10.0,
    EventType.relationship_change: 7.0,
    EventType.dialogue: 5.0,
    EventType.action: 4.0,
    EventType.environment: 3.0,
    EventType.director: 8.0,
}


class MemoryWriter:
    """从事件提取记忆，按 visibility 过滤谁该记住。"""

    def extract_memories(self, event: Event, character_names: list[str]) -> list[Memory]:
        visibility = event.visibility or event.participants or []
        importance = _IMPORTANCE_MAP.get(event.type, 5.0)
        memories: list[Memory] = []
        for name in character_names:
            if name in visibility:
                memories.append(Memory(
                    character_id=name,
                    world_id=event.world_id,
                    type="observation",
                    content=event.narration or f"Tick {event.tick} 事件",
                    tick=event.tick,
                    importance=importance,
                ))
        return memories
