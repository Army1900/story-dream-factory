import pytest
from app.worldbuilder.session import BuilderSession

def test_session_starts_at_vision():
    s = BuilderSession(template=None)
    assert s.current_stage == "vision"
    assert s.stage_index == 0

def test_advance_stage():
    s = BuilderSession(template=None)
    s.advance()
    assert s.current_stage == "setting"

def test_advance_past_final_returns_none():
    s = BuilderSession(template=None)
    for _ in range(7):
        s.advance()
    assert s.advance() is None  # 已到 finalize 之后

def test_go_back():
    s = BuilderSession(template=None)
    s.advance()  # setting
    s.advance()  # rules
    s.go_back()  # setting
    assert s.current_stage == "setting"

def test_go_back_from_first_stays():
    s = BuilderSession(template=None)
    s.go_back()
    assert s.current_stage == "vision"

def test_collect_data():
    s = BuilderSession(template=None)
    s.collect("vision", {"type":"奇幻","tone":"黑暗"})
    assert s.collected["vision"]["type"] == "奇幻"

def test_template_pre_fills():
    tpl = {"name":"t","genre":"fantasy","rules_draft":["r1"],"visual_style_draft":{"art":"oil"}}
    s = BuilderSession(template=tpl)
    assert s.collected["rules"] == ["r1"]
    assert s.collected["visual_style"]["art"] == "oil"

def test_checklist_progress():
    s = BuilderSession(template=None)
    s.collect("vision", {"type":"奇幻","tone":"黑暗","visual_style":{"art":"oil"}})
    progress = s.checklist_progress()
    assert progress["vision"]["covered"] >= 2  # type + visual_style

def test_serialize_deserialize():
    s = BuilderSession(template=None)
    s.collect("vision", {"type":"奇幻"})
    s.advance()
    data = s.to_dict()
    s2 = BuilderSession.from_dict(data)
    assert s2.current_stage == "setting"
    assert s2.collected["vision"]["type"] == "奇幻"
