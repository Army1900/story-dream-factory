import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.character_agent import CharacterAgent
from app.agents.proposal import ActionProposal
from app.models.character import Character
from app.models.memory import Memory

def _mock_llm(json_reply=None):
    llm = MagicMock()
    llm.complete = AsyncMock(return_value="回复")
    llm.complete_json = AsyncMock(return_value=json_reply or {
        "intent": "质问", "action_type": "dialogue",
        "target": "贝拉", "expectation": "真相", "dialogue": "你骗了我。"
    })
    return llm

def _make_character():
    return Character(
        id="c1", world_id="w1", name="艾伦",
        personality={"neuroticism": 0.8},
        backstory="流亡骑士",
        goals={"short_term": "复仇"},
        state={"location_id": "loc1", "health": 80, "mood": "愤怒"},
    )

def test_perceive_returns_context_string():
    llm = _mock_llm()
    agent = CharacterAgent(_make_character(), llm)
    snapshot = {"location": "酒馆", "present": ["艾伦", "贝拉"], "recent_events": ["T11 贝拉独坐"]}
    context = agent.perceive(snapshot)
    assert "酒馆" in context
    assert "贝拉" in context

@pytest.mark.asyncio
async def test_decide_returns_proposal():
    llm = _mock_llm()
    agent = CharacterAgent(_make_character(), llm)
    snapshot = {"location": "酒馆", "present": ["艾伦", "贝拉"], "recent_events": []}
    proposal = await agent.decide(snapshot)
    assert isinstance(proposal, ActionProposal)
    assert proposal.target == "贝拉"
    assert llm.complete_json.await_count == 1

@pytest.mark.asyncio
async def test_decide_prompt_includes_personality():
    llm = _mock_llm()
    agent = CharacterAgent(_make_character(), llm)
    snapshot = {"location": "酒馆", "present": ["贝拉"], "recent_events": []}
    await agent.decide(snapshot)
    # 验证 LLM 被调用（prompt 在 messages 里）
    call = llm.complete_json.call_args
    messages = call.kwargs.get("messages") or call.args[0]
    full_text = str(messages)
    assert "艾伦" in full_text  # 名字
    assert "复仇" in full_text or "流亡" in full_text  # 背景或目标

@pytest.mark.asyncio
async def test_decide_handles_llm_error():
    llm = MagicMock()
    llm.complete_json = AsyncMock(side_effect=Exception("LLM down"))
    agent = CharacterAgent(_make_character(), llm)
    snapshot = {"location": "酒馆", "present": [], "recent_events": []}
    proposal = await agent.decide(snapshot)
    # 降级：返回 wait 提案
    assert proposal.action_type == "wait"


@pytest.mark.asyncio
async def test_decide_uses_retrieved_memories():
    llm = _mock_llm(json_reply={"intent":"质问","action_type":"dialogue","target":"贝拉","expectation":"","dialogue":"你骗了我。"})
    memories = [
        Memory(character_id="c1", world_id="w1", content="贝拉三年前为我锻剑", importance=9, tick=1),
        Memory(character_id="c1", world_id="w1", content="今天下了雪", importance=2, tick=10),
    ]
    agent = CharacterAgent(_make_character(), llm, memories=memories)
    snapshot = {"location":"酒馆","present":["贝拉"],"recent_events":[]}
    await agent.decide(snapshot)
    # 验证 prompt 包含高重要性记忆
    call = llm.complete_json.call_args
    messages = call.kwargs.get("messages") or call.args[0]
    assert "锻剑" in str(messages)  # 高重要性记忆被检索
