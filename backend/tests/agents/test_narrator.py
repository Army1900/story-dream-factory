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
    assert "等待" in event.narration or "静" in event.narration  # 降级模板含关键词
