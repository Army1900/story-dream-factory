from app.models.event import Event
from app.models.enums import EventType


def test_event_defaults():
    e = Event(world_id="w1", tick=0)
    assert e.world_id == "w1"
    assert e.tick == 0
    assert e.type == EventType.action
    assert e.participants == []
    assert e.payload == {}
    assert e.visibility == []
    assert e.narration == ""
    assert e.id


def test_event_with_payload():
    e = Event(
        world_id="w1",
        tick=3,
        type=EventType.dialogue,
        participants=["c1", "c2"],
        location_id="loc-1",
        payload={"text": "你骗了我！"},
        visibility=["c1", "c2"],
        narration="艾伦怒视着对方。",
    )
    assert e.type == EventType.dialogue
    assert e.payload["text"] == "你骗了我！"
