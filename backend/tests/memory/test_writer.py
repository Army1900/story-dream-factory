from app.memory.writer import MemoryWriter
from app.models.event import Event
from app.models.enums import EventType

def _event(tick, narration, participants, visibility=None):
    return Event(
        world_id="w1", tick=tick, type=EventType.action,
        participants=participants, narration=narration,
        visibility=visibility if visibility is not None else participants,
        payload={},
    )

def test_writer_extracts_for_visible_characters():
    writer = MemoryWriter()
    event = _event(5, "艾伦质问贝拉", ["艾伦", "贝拉"])
    memories = writer.extract_memories(event, character_names=["艾伦", "贝拉", "凯尔"])
    assert len(memories) == 2  # 艾伦和贝拉（凯尔不在 visibility）
    names = [m.character_id for m in memories]
    assert "艾伦" in names or any("艾伦" in str(m.content) for m in memories)

def test_writer_respects_visibility():
    writer = MemoryWriter()
    event = _event(5, "秘密会议", ["凯尔"], visibility=["凯尔"])
    memories = writer.extract_memories(event, character_names=["艾伦", "凯尔"])
    assert len(memories) == 1  # 只有凯尔记住

def test_writer_importance_based_on_event_type():
    writer = MemoryWriter()
    conflict = _event(5, "战斗", ["艾伦"])
    conflict.type = EventType.conflict
    dialogue = _event(5, "闲聊", ["艾伦"])
    dialogue.type = EventType.dialogue
    m1 = writer.extract_memories(conflict, ["艾伦"])[0]
    m2 = writer.extract_memories(dialogue, ["艾伦"])[0]
    assert m1.importance > m2.importance  # 冲突比闲聊更重要

def test_writer_content_is_narration():
    writer = MemoryWriter()
    event = _event(3, "暴风雪封镇", ["艾伦"])
    memories = writer.extract_memories(event, ["艾伦"])
    assert "暴风雪" in memories[0].content
