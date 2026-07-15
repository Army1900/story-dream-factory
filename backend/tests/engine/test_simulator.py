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


# ============================================ 增强叙事路径（world_dir 接线）

_SCENE_YAML = (
    "scene_type: 对峙\n"
    "atmosphere: 寒夜酒馆，炉火噼啪。\n"
    "dramatic_intent: 艾伦逼问贝拉。\n"
    "pacing: slow\n"
    "focus_characters: [艾伦, 贝拉]\n"
    "non_character_events: [窗外雪越下越大]\n"
)


def _make_routing_llm(narration: str = "炉火噼啪，艾伦推门而入，雪从肩头落下。贝拉攥紧了围裙。"):
    """LLM mock：按 prompt 内容路由 complete（场景导演 / 摘要 / 总叙述者）。"""
    llm = MagicMock()

    async def _complete(*args, **kwargs):
        messages = kwargs.get("messages") or (args[0] if args else [])
        text = str(messages)
        if "场景导演" in text:
            return _SCENE_YAML
        if "故事编辑" in text:
            return "压缩后的故事摘要。"
        return narration

    llm.complete = AsyncMock(side_effect=_complete)
    llm.complete_json = AsyncMock(return_value={
        "intent": "质问", "action_type": "dialogue",
        "target": "贝拉", "expectation": "真相", "dialogue": "你骗了我。",
    })
    return llm


@pytest.mark.asyncio
async def test_enhanced_tick_single_narration_event(tmp_path):
    """新路径：多角色同拍合并为 1 个总叙述事件（而非按地点分组的多事件）。"""
    llm = _make_routing_llm()
    sim = Simulator(_make_world_multi(), _make_chars(), llm, world_dir=str(tmp_path))
    events = await sim.tick()
    # 无导演注入 + 1 个总叙述事件
    assert len(events) == 1
    # 所有角色都作为参与者（即使凯尔在另一个地点）
    assert set(events[0].participants) == {"艾伦", "贝拉", "凯尔"}
    assert events[0].narration  # 非空


@pytest.mark.asyncio
async def test_enhanced_vs_legacy_grouping(tmp_path):
    """对照：同样 3 角色（2+1 分布），旧路径产 2 事件，新路径产 1 事件。"""
    # 旧路径
    legacy = Simulator(_make_world_multi(), _make_chars(), _mock_llm_multi())
    legacy_events = await legacy.tick()
    assert len(legacy_events) == 2
    # 新路径
    enhanced = Simulator(
        _make_world_multi(), _make_chars(), _make_routing_llm(), world_dir=str(tmp_path),
    )
    enhanced_events = await enhanced.tick()
    assert len(enhanced_events) == 1


@pytest.mark.asyncio
async def test_enhanced_event_carries_scene_direction(tmp_path):
    llm = _make_routing_llm()
    sim = Simulator(_make_world_multi(), _make_chars(), llm, world_dir=str(tmp_path))
    events = await sim.tick()
    payload = events[0].payload or {}
    assert payload.get("scene_type") == "对峙"
    assert "scene_direction" in payload


@pytest.mark.asyncio
async def test_enhanced_writes_story_state(tmp_path):
    """tick 后 story_state.yaml 落盘，last_narration 非空。"""
    from app.persistence.world_store import WorldStore
    llm = _make_routing_llm()
    sim = Simulator(_make_world_multi(), _make_chars(), llm, world_dir=str(tmp_path))
    await sim.tick()
    state = WorldStore().load_story_state(str(tmp_path))
    assert state is not None
    assert state.get("last_narration")
    assert "recent_narrations" in state


@pytest.mark.asyncio
async def test_enhanced_character_decide_receives_scene_context(tmp_path):
    """新路径下角色决策 prompt 应包含场景方向。"""
    llm = _make_routing_llm()
    sim = Simulator(_make_world_multi(), _make_chars(), llm, world_dir=str(tmp_path))
    await sim.tick()
    # complete_json 被调用（角色决策）
    assert llm.complete_json.await_count >= 1
    messages = llm.complete_json.call_args.kwargs.get("messages") or llm.complete_json.call_args.args[0]
    full = str(messages)
    assert "戏剧方向" in full or "艾伦逼问贝拉" in full  # 场景方向注入


@pytest.mark.asyncio
async def test_enhanced_persists_events_and_world(tmp_path):
    """新路径仍正常落盘 events / world。"""
    from app.persistence.world_store import WorldStore
    llm = _make_routing_llm()
    sim = Simulator(_make_world_multi(), _make_chars(), llm, world_dir=str(tmp_path))
    await sim.tick()
    assert (tmp_path / "events").exists()
    wd = WorldStore().load_world(str(tmp_path))
    assert wd["clock_tick"] >= 1


@pytest.mark.asyncio
async def test_enhanced_multiple_ticks_accumulate_history(tmp_path):
    llm = _make_routing_llm()
    sim = Simulator(_make_world_multi(), _make_chars(), llm, world_dir=str(tmp_path))
    for _ in range(3):
        await sim.tick()
    assert sim.world.clock_tick == 3
    # 每个 tick 产生 1 个总叙述事件
    assert len(sim.event_history) == 3


@pytest.mark.asyncio
async def test_enhanced_scene_director_failure_falls_back_to_legacy(tmp_path, monkeypatch):
    """SceneDirector 抛异常时降级到旧路径（不阻塞 tick）。"""
    from app.agents import scene_director as sd_mod

    async def _boom(*a, **kw):
        raise Exception("director down")

    monkeypatch.setattr(sd_mod.SceneDirector, "direct", _boom)
    # complete 用于旧路径 Narrator（降级时走 _narrate_grouped）
    llm = MagicMock()
    llm.complete = AsyncMock(return_value="叙述。")
    llm.complete_json = AsyncMock(return_value={
        "intent": "行动", "action_type": "action", "target": "", "expectation": "", "dialogue": "",
    })
    sim = Simulator(_make_world_multi(), _make_chars(), llm, world_dir=str(tmp_path))
    events = await sim.tick()
    # 降级到分组叙述：酒馆(艾伦+贝拉) + 谋士塔(凯尔) = 2 事件
    assert len(events) == 2


@pytest.mark.asyncio
async def test_enhanced_llm_failure_still_produces_narration(tmp_path):
    """LLM complete 失败时，SceneDirector 与 MasterNarrator 内部降级，tick 不阻塞。"""
    llm = MagicMock()
    llm.complete = AsyncMock(side_effect=Exception("LLM down"))
    llm.complete_json = AsyncMock(return_value={
        "intent": "质问", "action_type": "dialogue",
        "target": "贝拉", "expectation": "", "dialogue": "你骗了我。",
    })
    sim = Simulator(_make_world_multi(), _make_chars(), llm, world_dir=str(tmp_path))
    events = await sim.tick()
    assert len(events) == 1
    # MasterNarrator 降级为对白拼接，叙述非空且含对白
    assert events[0].narration
    assert "你骗了我" in events[0].narration
