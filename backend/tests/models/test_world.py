from app.models.world import World, WorldTemplate


def test_world_has_required_scalar_fields():
    world = World(name="艾尔德兰", vision="魔法衰落的王国")
    assert world.name == "艾尔德兰"
    assert world.vision == "魔法衰落的王国"
    assert world.clock_tick == 0
    assert world.rules == []
    assert world.state_flags == {}
    assert world.id  # 自动生成 UUID


def test_world_json_fields_accept_complex_values():
    world = World(
        name="t",
        vision="v",
        rules=["魔法稀有", "暴力会被通缉"],
        state_flags={"war_started": False},
        visual_style={"art_style": "oil-painting", "palette": "dark"},
        llm_config={"tier1": "openai/glm-4-plus"},
        initial_state={"opening_situation": "冬夜", "inciting_event": None},
    )
    assert world.rules == ["魔法稀有", "暴力会被通缉"]
    assert world.visual_style["art_style"] == "oil-painting"
    assert world.llm_config["tier1"] == "openai/glm-4-plus"


def test_world_template_defaults():
    tpl = WorldTemplate(name="中世纪奇幻", genre="fantasy")
    assert tpl.genre == "fantasy"
    assert tpl.rules_draft == []
    assert tpl.visual_style_draft == {}
