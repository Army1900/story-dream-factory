import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.narrator import Narrator
from app.agents.proposal import ActionProposal
from app.models.event import Event

def _mock_llm(narration="木门被推开，寒风涌入。"):
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=narration)
    return llm

@pytest.mark.asyncio
async def test_narrate_returns_event():
    llm = _mock_llm()
    narrator = Narrator(llm)
    proposal = ActionProposal(intent="闯入", action_type="conflict", target="贝拉")
    event = await narrator.narrate(proposal, world_name="艾尔德兰", tick=12, location="酒馆")
    assert isinstance(event, Event)
    assert event.tick == 12
    assert event.narration  # 非空叙述
    assert llm.complete.await_count == 1

@pytest.mark.asyncio
async def test_narrate_uses_world_setting():
    llm = _mock_llm("叙述文本")
    narrator = Narrator(llm)
    proposal = ActionProposal(intent="说话", action_type="dialogue", target="贝拉", dialogue="你骗了我。")
    await narrator.narrate(proposal, world_name="艾尔德兰", tick=12, location="酒馆", world_setting="魔法衰落的王国")
    call = llm.complete.call_args
    messages = call.kwargs.get("messages") or call.args[0]
    full = str(messages)
    assert "艾尔德兰" in full or "魔法" in full

@pytest.mark.asyncio
async def test_narrate_fallback_on_error():
    llm = MagicMock()
    llm.complete = AsyncMock(side_effect=Exception("LLM down"))
    narrator = Narrator(llm)
    proposal = ActionProposal(intent="等待", action_type="wait")
    event = await narrator.narrate(proposal, world_name="w", tick=1, location="loc")
    assert event.narration  # 降级叙述（非空）
    assert "时间" in event.narration or "凝固" in event.narration  # 降级文本


@pytest.mark.asyncio
async def test_narrate_fallback_uses_empty_string_on_empty_llm():
    """LLM 返回空字符串也应触发降级。"""
    llm = MagicMock()
    llm.complete = AsyncMock(return_value="   ")
    narrator = Narrator(llm)
    proposal = ActionProposal(intent="说话", action_type="dialogue", target="贝拉", dialogue="你骗了我。")
    event = await narrator.narrate(proposal, world_name="w", tick=1, location="loc")
    assert event.narration == "你骗了我。"  # 降级为对白本身


@pytest.mark.asyncio
async def test_narrate_fallback_dialogue_no_template_wrap():
    """对白降级不应再被「角色说出了心中的话」模板包裹。"""
    llm = MagicMock()
    llm.complete = AsyncMock(side_effect=Exception("LLM down"))
    narrator = Narrator(llm)
    proposal = ActionProposal(intent="说话", action_type="dialogue", target="贝拉", dialogue="你骗了我。")
    event = await narrator.narrate(proposal, world_name="w", tick=1, location="loc")
    assert event.narration == "你骗了我。"
    assert "心中的话" not in event.narration  # 不再有模板包装


@pytest.mark.asyncio
async def test_narrate_group_merges_multiple_proposals():
    """同地点多角色行动合并为一段叙述。"""
    llm = _mock_llm(narration="酒馆里，两人对视，空气紧绷。")
    narrator = Narrator(llm)
    proposals = [
        ActionProposal(intent="质问", action_type="dialogue", target="贝拉", dialogue="你骗了我。"),
        ActionProposal(intent="辩解", action_type="dialogue", target="艾伦", dialogue="听我解释。"),
    ]
    narration = await narrator.narrate_group(
        proposals=proposals, participants=["艾伦", "贝拉"],
        world_name="艾尔德兰", location="酒馆", world_setting="魔法衰落",
    )
    assert "酒馆" in narration
    assert llm.complete.await_count == 1
    # prompt 应包含两个角色名与场景合并要求
    messages = llm.complete.call_args.kwargs.get("messages") or llm.complete.call_args.args[0]
    full = str(messages)
    assert "艾伦" in full and "贝拉" in full


@pytest.mark.asyncio
async def test_narrate_group_fallback_on_error():
    llm = MagicMock()
    llm.complete = AsyncMock(side_effect=Exception("LLM down"))
    narrator = Narrator(llm)
    proposals = [
        ActionProposal(intent="质问", action_type="dialogue", dialogue="你骗了我。"),
        ActionProposal(intent="沉默", action_type="wait"),
    ]
    narration = await narrator.narrate_group(
        proposals=proposals, participants=["艾伦", "贝拉"],
        world_name="w", location="酒馆", world_setting="",
    )
    assert narration  # 非空降级
    assert "你骗了我" in narration
