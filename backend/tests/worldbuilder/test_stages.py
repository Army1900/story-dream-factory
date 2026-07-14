from app.worldbuilder.stages import STAGES, STAGE_ORDER

def test_stages_are_seven():
    assert len(STAGE_ORDER) == 7

def test_stage_order():
    assert STAGE_ORDER == ["vision","setting","rules","locations","characters","inciting","finalize"]

def test_each_stage_has_checklist():
    for key in STAGE_ORDER:
        s = STAGES[key]
        assert s["title"]
        assert isinstance(s["checklist"], list) and len(s["checklist"]) > 0
        assert s["prompt_hint"]

def test_vision_stage_has_visual_style():
    assert "视觉风格" in STAGES["vision"]["checklist"]
