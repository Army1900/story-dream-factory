import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.master_narrator import MasterNarrator
from app.agents.proposal import ActionProposal


NARRATION = (
    "炉火在角落里挣扎着跳动，把艾伦的影子拉长投到墙上。他推开酒馆的木门，"
    "夹带的雪在地板上很快化成一滩水痕。贝拉攥紧了围裙，指节发白。"
    "「你骗了我。」他的声音很轻，却像一把按在剑柄上的手——随时会出鞘。"
)


def _mock_llm(text: str = NARRATION, side_effect=None):
    llm = MagicMock()
    if side_effect is not None:
        llm.complete = AsyncMock(side_effect=side_effect)
    else:
        llm.complete = AsyncMock(return_value=text)
    return llm


def _scene():
    return {
        "scene_type": "对峙",
        "atmosphere": "寒夜酒馆，炉火噼啪",
        "dramatic_intent": "艾伦逼问贝拉",
        "pacing": "slow",
        "focus_characters": ["艾伦", "贝拉"],
        "non_character_events": ["窗外雪越下越大"],
    }


def _proposals():
    return [
        ActionProposal(intent="质问", action_type="dialogue", target="贝拉", dialogue="你骗了我。"),
        ActionProposal(intent="辩解", action_type="dialogue", target="艾伦", dialogue="听我解释。"),
    ]


class _Resolved:
    def __init__(self, success=True):
        self.success = success
        self.new_state = {"location_id": "断刃酒馆"}


def _world():
    return {"name": "艾尔德兰", "setting": "魔法衰落的王国"}


def _story():
    return {
        "narrative_summary": "艾伦归来质问贝拉。",
        "last_narration": "上一幕：空气凝固了。",
    }


@pytest.mark.asyncio
async def test_narrate_returns_string():
    llm = _mock_llm()
    text = await MasterNarrator(llm).narrate(
        scene_direction=_scene(), proposals=_proposals(), resolved=[_Resolved(), _Resolved()],
        world=_world(), story_state=_story(), tick=3, participants=["艾伦", "贝拉"],
    )
    assert isinstance(text, str)
    assert "炉火" in text
    assert llm.complete.await_count == 1


@pytest.mark.asyncio
async def test_narrate_fallback_on_error():
    llm = _mock_llm(side_effect=Exception("LLM down"))
    text = await MasterNarrator(llm).narrate(
        scene_direction=_scene(), proposals=_proposals(), resolved=[_Resolved(), _Resolved()],
        world=_world(), story_state=_story(), tick=1, participants=["艾伦", "贝拉"],
    )
    # 降级：拼接对白
    assert "你骗了我" in text
    assert "听我解释" in text


@pytest.mark.asyncio
async def test_narrate_fallback_on_empty():
    llm = _mock_llm(text="   ")
    text = await MasterNarrator(llm).narrate(
        scene_direction=_scene(), proposals=_proposals(), resolved=[_Resolved(), _Resolved()],
        world=_world(), story_state=_story(), tick=1, participants=["艾伦", "贝拉"],
    )
    assert "你骗了我" in text  # 降级


@pytest.mark.asyncio
async def test_narrate_fallback_no_dialogue_uses_intent():
    llm = _mock_llm(side_effect=Exception("LLM down"))
    proposals = [ActionProposal(intent="悄悄靠近", action_type="move", target="酒馆")]
    text = await MasterNarrator(llm).narrate(
        scene_direction=_scene(), proposals=proposals, resolved=[_Resolved()],
        world=_world(), story_state=_story(), tick=1, participants=["凯尔"],
    )
    assert "悄悄靠近" in text


@pytest.mark.asyncio
async def test_narrate_prompt_contains_scene_and_actions():
    llm = _mock_llm()
    await MasterNarrator(llm).narrate(
        scene_direction=_scene(), proposals=_proposals(), resolved=[_Resolved(), _Resolved()],
        world=_world(), story_state=_story(), tick=3, participants=["艾伦", "贝拉"],
    )
    messages = llm.complete.call_args.kwargs.get("messages") or llm.complete.call_args.args[0]
    full = str(messages)
    # 世界信息
    assert "艾尔德兰" in full
    # 场景方向
    assert "对峙" in full
    assert "艾伦逼问贝拉" in full or "dramatic_intent" in full or "意图" in full
    # 角色行动（含名字、对白）
    assert "艾伦" in full and "贝拉" in full
    assert "你骗了我" in full
    # 衔接与摘要
    assert "空气凝固" in full
    # 比例要求
    assert "25-30%" in full or "场景与环境描写" in full
    # 禁止项
    assert "心中的话" in full  # 禁止模板被写进 prompt


@pytest.mark.asyncio
async def test_narrate_uses_participants_for_action_names():
    llm = _mock_llm()
    await MasterNarrator(llm).narrate(
        scene_direction=_scene(), proposals=_proposals(), resolved=[_Resolved(), _Resolved()],
        world=_world(), story_state=_story(), tick=1, participants=["艾伦", "贝拉"],
    )
    messages = llm.complete.call_args.kwargs.get("messages") or llm.complete.call_args.args[0]
    full = str(messages)
    # 行动列表以角色名开头
    assert "艾伦（dialogue）" in full
    assert "贝拉（dialogue）" in full


@pytest.mark.asyncio
async def test_narrate_without_participants_uses_generic_names():
    llm = _mock_llm()
    await MasterNarrator(llm).narrate(
        scene_direction=_scene(), proposals=[_proposals()[0]], resolved=[_Resolved()],
        world=_world(), story_state=_story(), tick=1, participants=None,
    )
    messages = llm.complete.call_args.kwargs.get("messages") or llm.complete.call_args.args[0]
    full = str(messages)
    assert "角色1" in full  # 兜底命名


@pytest.mark.asyncio
async def test_narrate_marks_failed_action():
    llm = _mock_llm()
    await MasterNarrator(llm).narrate(
        scene_direction=_scene(),
        proposals=[ActionProposal(intent="攻击", action_type="conflict", target="贝拉")],
        resolved=[_Resolved(success=False)],
        world=_world(), story_state=_story(), tick=1, participants=["艾伦"],
    )
    messages = llm.complete.call_args.kwargs.get("messages") or llm.complete.call_args.args[0]
    full = str(messages)
    assert "受挫" in full  # 失败被标注
