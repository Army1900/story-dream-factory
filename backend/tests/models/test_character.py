from app.models.character import Character
from app.models.relationship import Relationship


def test_character_defaults():
    c = Character(name="艾伦", world_id="w1")
    assert c.name == "艾伦"
    assert c.goals == {}
    assert c.state == {}
    assert c.personality == {}
    assert c.visual_definition == {}
    assert c.id


def test_character_with_complex_fields():
    c = Character(
        name="艾伦",
        world_id="w1",
        archetype="流亡者",
        personality={"openness": 0.3, "neuroticism": 0.8},
        backstory="曾是骑士",
        skills=["剑术", "生存"],
        goals={"short_term": "复仇", "long_term": " redemption"},
        state={"location_id": "loc-1", "health": 80, "mood": "愤怒"},
        visual_definition={"description": "黑发疤脸", "reference_image_url": None},
    )
    assert c.skills == ["剑术", "生存"]
    assert c.state["health"] == 80


def test_relationship_defaults():
    r = Relationship(
        world_id="w1", from_character_id="c1", to_character_id="c2"
    )
    assert r.affinity == 0.0
    assert r.trust == 0.0
    assert r.history == []
    assert r.id
