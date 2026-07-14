from __future__ import annotations
from fastapi import APIRouter
from app.api.simulation import _SIMULATORS

router = APIRouter(prefix="/worlds/{world_id}/director", tags=["director"])

@router.post("/inject")
def inject_directive(world_id: str, payload: dict):
    """导演介入：注入事件/改目标/改规则/强制行动。"""
    dtype = payload.get("type", "inject_event")
    data = payload.get("payload", {})
    target = payload.get("target", "")
    # 找到该世界的 simulator
    sim = None
    for s in _SIMULATORS.values():
        if s.world.id == world_id:
            sim = s
            break
    if sim:
        sim.directives = getattr(sim, 'directives', [])
        sim.directives.append({"type": dtype, "payload": data, "target": target})
        return {"status": "queued", "world_id": world_id, "directive_type": dtype}
    return {"status": "queued", "world_id": world_id, "directive_type": dtype, "note": "will apply on next tick"}
