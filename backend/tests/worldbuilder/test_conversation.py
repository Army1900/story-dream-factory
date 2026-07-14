import pytest
from unittest.mock import AsyncMock, MagicMock
from app.worldbuilder.session import BuilderSession
from app.worldbuilder.conversation import ConversationService

def _mock_llm(reply="好的，收到。", extracted=None):
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=reply)
    llm.complete_json = AsyncMock(return_value=extracted or {})
    return llm

@pytest.mark.asyncio
async def test_conversation_returns_reply():
    llm = _mock_llm("你想讲什么样的故事？")
    svc = ConversationService(llm)
    session = BuilderSession(template=None)
    reply = await svc.process_message(session, "我想讲一个黑暗奇幻故事")
    assert "黑暗奇幻" in reply or len(reply) > 0
    assert llm.complete.await_count == 1

@pytest.mark.asyncio
async def test_conversation_extracts_structured_data():
    llm = _mock_llm("收到", {"type":"奇幻","tone":"黑暗","visual_style":{"art_style":"油画"}})
    svc = ConversationService(llm)
    session = BuilderSession(template=None)
    await svc.process_message(session, "黑暗奇幻")
    assert session.collected.get("vision", {}).get("type") == "奇幻"

@pytest.mark.asyncio
async def test_advance_when_user_says_next():
    llm = _mock_llm()
    svc = ConversationService(llm)
    session = BuilderSession(template=None)
    await svc.process_message(session, "完成，下一步")
    assert session.current_stage == "setting"

@pytest.mark.asyncio
async def test_go_back_when_user_says_back():
    llm = _mock_llm()
    svc = ConversationService(llm)
    session = BuilderSession(template=None)
    session.advance()  # setting
    await svc.process_message(session, "回到上一步")
    assert session.current_stage == "vision"

@pytest.mark.asyncio
async def test_message_recorded():
    llm = _mock_llm("回复")
    svc = ConversationService(llm)
    session = BuilderSession(template=None)
    await svc.process_message(session, "hello")
    assert len(session.messages) == 2  # user + assistant
    assert session.messages[0]["role"] == "user"
    assert session.messages[1]["role"] == "assistant"
