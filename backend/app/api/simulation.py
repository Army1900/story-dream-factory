from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.api.deps import get_session
from app.models.world import World
from app.models.character import Character
from app.engine.simulator import Simulator

router = APIRouter(prefix="/worlds/{world_id}/simulate", tags=["simulation"])

_SIMULATORS: dict[str, Simulator] = {}


def _get_llm():
    from app.config import get_settings
    from app.llm.config import TierConfig, LLMRoutingConfig
    from app.llm.gateway import LLMGateway
    settings = get_settings()
    routing = LLMRoutingConfig(
        tiers={"tier1": TierConfig(model=settings.llm_tier1_model)},
        default_tier="tier1",
    )
    return LLMGateway(routing=routing, api_key=settings.zhipu_api_key)


@router.post("/start")
def start_simulation(world_id: str, session_db: Session = Depends(get_session)):
    world = session_db.get(World, world_id)
    if not world:
        return {"error": "world not found"}
    chars = list(session_db.exec(select(Character).where(Character.world_id == world_id)).all())
    llm = _get_llm()
    sim = Simulator(world, chars, llm)
    sim_id = str(uuid.uuid4())
    _SIMULATORS[sim_id] = sim
    return {"sim_id": sim_id, "world": world.name, "characters": [c.name for c in chars], "tick": world.clock_tick}


@router.post("/step")
async def step_simulation(world_id: str):
    # 找到该世界的 simulator
    sim = None
    for sid, s in _SIMULATORS.items():
        if s.world.id == world_id:
            sim = s
            break
    if not sim:
        return {"error": "no active simulation for this world"}
    events = await sim.tick()
    return {
        "tick": sim.world.clock_tick,
        "events": [
            {"tick": e.tick, "type": e.type.value if hasattr(e.type, 'value') else str(e.type),
             "narration": e.narration, "participants": e.participants}
            for e in events
        ],
    }


@router.get("/status")
def simulation_status(world_id: str):
    sim = None
    for sid, s in _SIMULATORS.items():
        if s.world.id == world_id:
            sim = s
            break
    if not sim:
        return {"error": "no active simulation"}
    return {
        "tick": sim.world.clock_tick,
        "total_events": len(sim.event_history),
        "recent_narrations": [e.narration for e in sim.event_history[-5:]],
    }
