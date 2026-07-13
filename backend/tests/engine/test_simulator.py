import pytest
from unittest.mock import AsyncMock, MagicMock
from app.engine.simulator import Simulator
from app.models.world import World
from app.models.character import Character
from app.agents.proposal import ActionProposal
from app.models.event import Event

def _mock_llm():
    llm = MagicMock()
    llm.complete = AsyncMock(return_value="寒风卷着雪花涌入酒馆。")
    llm.complete_json = AsyncMock(return_value={
        "intent": "质问", "action_type": "dialogue",
        "target": "贝拉", "expectation": "真相", "dialogue": "你骗了我。"
    })
    return llm

def _make_world():
    return World(id="w1", name="艾尔德兰", setting="魔法衰落的王国", clock_tick=0)

def _make_character():
    return Character(id="c1", world_id="w1", name="艾伦",
                     personality={"neuroticism": 0.8}, backstory="流亡骑士",
                     goals={"short_term": "复仇"}, state={"location_id": "酒馆", "mood": "愤怒"})

@pytest.mark.asyncio
async def test_tick_returns_event():
    llm = _mock_llm()
    sim = Simulator(_make_world(), [_make_character()], llm)
    events = await sim.tick()
    assert len(events) >= 1
    assert isinstance(events[0], Event)
    assert events[0].narration  # 非空叙述

@pytest.mark.asyncio
async def test_tick_advances_clock():
    llm = _mock_llm()
    world = _make_world()
    sim = Simulator(world, [_make_character()], llm)
    assert world.clock_tick == 0
    await sim.tick()
    assert world.clock_tick == 1

@pytest.mark.asyncio
async def test_tick_event_has_correct_tick():
    llm = _mock_llm()
    world = _make_world()
    sim = Simulator(world, [_make_character()], llm)
    events = await sim.tick()
    assert events[0].tick == 0  # 事件记录的是推进前的 tick

@pytest.mark.asyncio
async def test_multiple_ticks():
    llm = _mock_llm()
    world = _make_world()
    sim = Simulator(world, [_make_character()], llm)
    await sim.tick()
    await sim.tick()
    await sim.tick()
    assert world.clock_tick == 3
    assert len(sim.event_history) == 3

@pytest.mark.asyncio
async def test_world_snapshot_built():
    llm = _mock_llm()
    sim = Simulator(_make_world(), [_make_character()], llm)
    snapshot = sim._build_snapshot()
    assert snapshot["location"]  # 有地点
    assert "艾伦" in snapshot["present"]
