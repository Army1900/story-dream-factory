import pytest
from unittest.mock import AsyncMock, MagicMock
from app.memory.reflection import Reflector
from app.models.memory import Memory

def _mock_llm(insight="我发现贝拉一直在骗我。"):
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=insight)
    return llm

def test_should_reflect_false_below_threshold():
    reflector = Reflector(llm=_mock_llm(), interval=5)
    assert not reflector.should_reflect(current_tick=3, memory_count=10)

def test_should_reflect_true_at_interval():
    reflector = Reflector(llm=_mock_llm(), interval=5)
    assert reflector.should_reflect(current_tick=5, memory_count=10)
    assert reflector.should_reflect(current_tick=10, memory_count=10)

def test_should_reflect_false_low_memory():
    reflector = Reflector(llm=_mock_llm(), interval=5)
    assert not reflector.should_reflect(current_tick=10, memory_count=2)  # 记忆太少

@pytest.mark.asyncio
async def test_reflect_returns_insight_memory():
    llm = _mock_llm("凯尔才是幕后黑手。")
    reflector = Reflector(llm=llm, interval=5)
    memories = [
        Memory(character_id="c1", world_id="w1", content="发现密信", importance=9, tick=4),
        Memory(character_id="c1", world_id="w1", content="贝拉说谎", importance=7, tick=8),
        Memory(character_id="c1", world_id="w1", content="夜半脚步声", importance=6, tick=6),
        Memory(character_id="c1", world_id="w1", content="凯尔露出破绽", importance=8, tick=7),
        Memory(character_id="c1", world_id="w1", content="剑上的刻纹", importance=5, tick=5),
    ]
    result = await reflector.reflect(memories, character_name="艾伦", current_tick=10)
    assert result is not None
    assert "凯尔" in result.content or "黑手" in result.content
    assert result.importance >= 8.0  # 反思是高重要性
    assert result.type == "reflection"

@pytest.mark.asyncio
async def test_reflect_none_when_not_ready():
    llm = _mock_llm()
    reflector = Reflector(llm=llm, interval=5)
    result = await reflector.reflect([], character_name="x", current_tick=2)
    assert result is None
