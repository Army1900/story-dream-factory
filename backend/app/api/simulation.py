from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from app.config import get_settings
from app.engine.simulator import Simulator
from app.models.character import Character
from app.models.world import World
from app.persistence.world_store import WorldStore

router = APIRouter(prefix="/worlds/{world_id}/simulate", tags=["simulation"])

# world_id（= 世界目录名）→ Simulator
_SIMULATORS: dict[str, Simulator] = {}

_store = WorldStore()


def _get_llm():
    from app.config import get_settings
    from app.llm.config import LLMRoutingConfig, TierConfig
    from app.llm.gateway import LLMGateway

    settings = get_settings()
    routing = LLMRoutingConfig(
        tiers={"tier1": TierConfig(model=settings.llm_tier1_model)},
        default_tier="tier1",
    )
    return LLMGateway(routing=routing, api_key=settings.zhipu_api_key)


def _world_dir(world_id: str) -> Path:
    return Path(get_settings().worlds_dir) / world_id


def _build_sim_from_files(world_id: str) -> Simulator | None:
    """从 world.yaml 构造 Simulator（含 world_dir 接线 + 已存 directives）。"""
    world_dir = _world_dir(world_id)
    wd = _store.load_world(world_dir)
    if wd is None:
        return None

    world = World(
        id=wd.get("id", world_id),
        name=wd.get("name", world_id),
        vision=wd.get("vision", "") or "",
        setting=wd.get("setting", "") or "",
        rules=wd.get("rules", []) or [],
        visual_style=wd.get("visual_style", {}) or {},
        clock_tick=wd.get("clock_tick", 0) or 0,
        clock_date=wd.get("clock_date", "") or "",
        state_flags=wd.get("state_flags", {}) or {},
        initial_state=wd.get("initial_state", {}) or {},
    )

    chars: list[Character] = []
    for cd in wd.get("characters", []) or []:
        if not isinstance(cd, dict):
            continue
        chars.append(
            Character(
                id=cd.get("id", cd.get("name", "")),
                world_id=world.id,
                name=cd.get("name", ""),
                archetype=cd.get("archetype", "") or "",
                personality=cd.get("personality", {}) or {},
                backstory=cd.get("backstory", "") or "",
                skills=cd.get("skills", []) or [],
                goals=cd.get("goals", {}) or {},
                state=cd.get("state", {}) or {},
                visual_definition=cd.get("visual_definition", {}) or {},
            )
        )

    sim = Simulator(world, chars, _get_llm(), world_dir=str(world_dir))

    # 加载已存导演指令（重启后续跑场景）
    existing = _store.load_directives(world_dir)
    if existing:
        sim.directives = existing

    return sim


def get_or_load_sim(world_id: str) -> Simulator | None:
    """先查内存；不在则从文件加载并缓存（供 director / websocket 复用）。"""
    sim = _SIMULATORS.get(world_id)
    if sim is not None:
        return sim
    # 兜底：按 world.id / world.name 匹配（历史键）
    for s in _SIMULATORS.values():
        if s.world.id == world_id or s.world.name == world_id:
            return s
    sim = _build_sim_from_files(world_id)
    if sim is not None:
        _SIMULATORS[world_id] = sim
    return sim


@router.post("/start")
def start_simulation(world_id: str):
    sim = get_or_load_sim(world_id)
    if sim is None:
        return {"error": "world not found"}
    return {
        "sim_id": world_id,
        "world": sim.world.name,
        "characters": [c.name for c in sim.characters],
        "tick": sim.world.clock_tick,
    }


@router.post("/step")
async def step_simulation(world_id: str):
    sim = get_or_load_sim(world_id)
    if sim is None:
        return {"error": "no active simulation for this world"}
    events = await sim.tick()
    return {
        "tick": sim.world.clock_tick,
        "events": [
            {
                "tick": e.tick,
                "type": e.type.value if hasattr(e.type, "value") else str(e.type),
                "narration": e.narration,
                "participants": e.participants,
            }
            for e in events
        ],
    }


@router.get("/status")
def simulation_status(world_id: str):
    sim = get_or_load_sim(world_id)
    if sim is None:
        return {"error": "no active simulation"}
    return {
        "tick": sim.world.clock_tick,
        "total_events": len(sim.event_history),
        "recent_narrations": [e.narration for e in sim.event_history[-5:]],
    }
