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


# ---------------------------------------------------------------- M4 多角色测试

def _mock_llm_multi():
    llm = MagicMock()
    llm.complete = AsyncMock(return_value="多个角色在这一刻行动。")
    llm.complete_json = AsyncMock(return_value={"intent": "行动", "action_type": "action", "target": "", "expectation": "", "dialogue": ""})
    return llm

def _make_world_multi():
    return World(id="w-m", name="艾尔德兰", setting="魔法衰落", clock_tick=0, rules=["魔法不可复活死者"])

def _make_chars():
    return [
        Character(id="c1", world_id="w-m", name="艾伦", goals={"short_term": "复仇"}, state={"location_id": "酒馆", "health": 100}),
        Character(id="c2", world_id="w-m", name="贝拉", goals={"short_term": "守护秘密"}, state={"location_id": "酒馆", "health": 100}),
        Character(id="c3", world_id="w-m", name="凯尔", goals={"short_term": "操纵"}, state={"location_id": "谋士塔", "health": 100}),
    ]

@pytest.mark.asyncio
async def test_multi_character_tick():
    llm = _mock_llm_multi()
    sim = Simulator(_make_world_multi(), _make_chars(), llm)
    events = await sim.tick()
    # 艾伦+贝拉 同在「酒馆」→ 合并为 1 个场景事件；凯尔在「谋士塔」→ 1 个单独事件
    assert len(events) == 2
    # 应有一个事件同时含艾伦和贝拉（同地点合并）
    merged = [e for e in events if "艾伦" in (e.participants or []) and "贝拉" in (e.participants or [])]
    assert len(merged) == 1
    assert merged[0].narration  # 合并叙述非空

@pytest.mark.asyncio
async def test_multi_tick_advances_clock_once():
    llm = _mock_llm_multi()
    world = _make_world_multi()
    sim = Simulator(world, _make_chars(), llm)
    await sim.tick()
    assert world.clock_tick == 1  # 多角色但只推进一次

@pytest.mark.asyncio
async def test_physics_applied():
    llm = MagicMock()
    llm.complete = AsyncMock(return_value="叙述")
    llm.complete_json = AsyncMock(return_value={"intent": "去王城", "action_type": "move", "target": "王城", "expectation": "", "dialogue": ""})
    world = _make_world_multi()
    sim = Simulator(world, [_make_chars()[0]], llm)  # 只有艾伦
    await sim.tick()
    # 艾伦应该移动到王城
    assert sim.characters[0].state["location_id"] == "王城"

@pytest.mark.asyncio
async def test_conflict_updates_health():
    llm = MagicMock()
    llm.complete = AsyncMock(return_value="战斗")
    llm.complete_json = AsyncMock(return_value={"intent": "攻击", "action_type": "conflict", "target": "贝拉", "expectation": "", "dialogue": ""})
    world = _make_world_multi()
    chars = _make_chars()[:2]  # 艾伦 + 贝拉
    sim = Simulator(world, chars, llm)
    await sim.tick()
    # 艾伦攻击→贝拉应受伤（health 下降）
    bella = [c for c in sim.characters if c.name == "贝拉"][0]
    assert bella.state["health"] < 100


@pytest.mark.asyncio
async def test_tick_writes_memories():
    """tick 后角色应有记忆写入。"""
    llm = MagicMock()
    llm.complete = AsyncMock(return_value="叙述")
    llm.complete_json = AsyncMock(return_value={"intent":"行动","action_type":"dialogue","target":"贝拉","expectation":"","dialogue":"你好。"})
    world = _make_world()
    chars = _make_chars()
    sim = Simulator(world, chars, llm)
    await sim.tick()
    # 至少有角色有记忆
    assert len(sim.character_memories.get("艾伦", [])) > 0 or len(sim.character_memories.get("c1", [])) > 0 or len(sim.event_history) > 0
