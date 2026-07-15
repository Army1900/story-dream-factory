import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.scene_director import SceneDirector


VALID_YAML = (
    "scene_type: 对峙\n"
    "atmosphere: 寒风卷雪涌入，炉火噼啪作响，空气里弥漫着麦酒与铁锈的味道。\n"
    "dramatic_intent: 艾伦从贝拉的回避中察觉到更深的秘密，逼问升级。\n"
    "pacing: slow\n"
    "focus_characters: [艾伦, 贝拉]\n"
    "non_character_events: [窗外雪越下越大, 远处传来夜钟声]\n"
)


def _mock_llm(raw: str = VALID_YAML, side_effect=None):
    llm = MagicMock()
    if side_effect is not None:
        llm.complete = AsyncMock(side_effect=side_effect)
    else:
        llm.complete = AsyncMock(return_value=raw)
    return llm


def _world():
    return {"name": "艾尔德兰", "setting": "魔法衰落的王国", "rules": ["魔法不可复活死者"]}


def _story():
    return {
        "phase": "rising_action",
        "narrative_summary": "艾伦归来，在断刃酒馆质问贝拉。",
        "last_narration": "空气凝固了。",
        "open_threads": [{"description": "贝拉为何背叛", "intensity": 0.8}],
        "dramatic_tensions": [{"between": ["艾伦", "凯尔"], "type": "复仇", "intensity": 0.9}],
    }


def _chars():
    return [
        {"name": "艾伦", "location": "断刃酒馆", "mood": "愤怒", "goal": "复仇"},
        {"name": "贝拉", "location": "断刃酒馆", "mood": "恐惧", "goal": "隐瞒"},
    ]


@pytest.mark.asyncio
async def test_direct_returns_normalized_dict():
    llm = _mock_llm()
    d = await SceneDirector(llm).direct(_world(), _story(), tick=5, character_states=_chars())
    assert d["scene_type"] == "对峙"
    assert "寒风" in d["atmosphere"]
    assert d["pacing"] == "slow"
    assert d["focus_characters"] == ["艾伦", "贝拉"]
    assert "窗外雪越下越大" in d["non_character_events"]
    # 必须包含所有规范字段
    for key in ("scene_type", "atmosphere", "dramatic_intent", "pacing",
                "focus_characters", "non_character_events"):
        assert key in d


@pytest.mark.asyncio
async def test_direct_complete_called_once():
    llm = _mock_llm()
    await SceneDirector(llm).direct(_world(), _story(), tick=1, character_states=_chars())
    assert llm.complete.await_count == 1


@pytest.mark.asyncio
async def test_direct_prompt_contains_world_and_story():
    llm = _mock_llm()
    await SceneDirector(llm).direct(_world(), _story(), tick=7, character_states=_chars())
    messages = llm.complete.call_args.kwargs.get("messages") or llm.complete.call_args.args[0]
    full = str(messages)
    assert "艾尔德兰" in full          # 世界名
    assert "魔法衰落的王国" in full     # 设定
    assert "rising_action" in full     # 阶段
    assert "艾伦" in full and "贝拉" in full  # 角色
    assert "断刃酒馆" in full           # 角色地点
    assert "YAML" in full               # 输出格式要求


@pytest.mark.asyncio
async def test_direct_fallback_on_non_yaml():
    """LLM 返回非 YAML-dict（纯文本）时降级为默认值，不抛异常。"""
    llm = _mock_llm(raw="这不是yaml，就是一句话。")
    d = await SceneDirector(llm).direct(_world(), _story(), tick=1, character_states=_chars())
    assert d["scene_type"]  # 有默认值
    assert d["pacing"] == "medium"
    assert d["focus_characters"] == []


@pytest.mark.asyncio
async def test_direct_fallback_on_empty():
    llm = _mock_llm(raw="")
    d = await SceneDirector(llm).direct(_world(), _story(), tick=1, character_states=_chars())
    assert d["scene_type"]  # 默认
    assert d["pacing"] == "medium"


@pytest.mark.asyncio
async def test_direct_fallback_on_exception():
    llm = _mock_llm(side_effect=Exception("LLM down"))
    d = await SceneDirector(llm).direct(_world(), _story(), tick=1, character_states=_chars())
    assert d["scene_type"]  # 默认
    assert d["pacing"] == "medium"


@pytest.mark.asyncio
async def test_direct_partial_yaml_filled_with_defaults():
    """LLM 只返回部分字段时，缺失字段用默认值补齐。"""
    partial = "scene_type: 揭露\npacing: fast\n"
    llm = _mock_llm(raw=partial)
    d = await SceneDirector(llm).direct(_world(), _story(), tick=1, character_states=_chars())
    assert d["scene_type"] == "揭露"
    assert d["pacing"] == "fast"
    assert d["atmosphere"] == ""           # 缺失→空字符串
    assert d["focus_characters"] == []     # 缺失→空列表
    assert d["non_character_events"] == []


@pytest.mark.asyncio
async def test_direct_scalar_focus_coerced_to_list():
    """focus_characters 给成单个标量也应容错成列表。"""
    raw = "scene_type: 日常\nfocus_characters: 艾伦\n"
    llm = _mock_llm(raw=raw)
    d = await SceneDirector(llm).direct(_world(), _story(), tick=1, character_states=_chars())
    assert d["focus_characters"] == ["艾伦"]
