from app.models.memory import Memory
from app.models.image_asset import ImageAsset
from app.models.director import DirectorDirective
from app.models.enums import MemoryType, ImageAssetType, DirectiveType


def test_memory_defaults():
    m = Memory(character_id="c1", world_id="w1")
    assert m.type == MemoryType.observation
    assert m.content == ""
    assert m.importance == 5.0
    assert m.embedding == []


def test_image_asset_defaults():
    a = ImageAsset(world_id="w1")
    assert a.type == ImageAssetType.style_ref
    assert a.prompt == ""
    assert a.seed == 0
    assert a.reference_image_ids == []
    assert a.url == ""


def test_directive_defaults():
    d = DirectorDirective(world_id="w1", effective_tick=5)
    assert d.type == DirectiveType.inject_event
    assert d.payload == {}
    assert d.target == ""
    assert d.effective_tick == 5
