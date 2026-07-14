from __future__ import annotations

from fastapi import APIRouter

from app.api.simulation import _SIMULATORS, _world_dir, _store

router = APIRouter(prefix="/worlds/{world_id}/director", tags=["director"])


@router.post("/inject")
def inject_directive(world_id: str, payload: dict):
    """导演介入：注入事件/改目标/改规则/强制行动。

    指令同时写入 ``directives.yaml``（持久化）和内存 Simulator（如已启动）。
    """
    dtype = payload.get("type", "inject_event")
    data = payload.get("payload", {})
    target = payload.get("target", "")
    directive = {"type": dtype, "payload": data, "target": target}

    # ① 持久化到 directives.yaml（append）
    world_dir = _world_dir(world_id)
    existing = _store.load_directives(world_dir)
    existing.append(directive)
    _store.save_directives(world_dir, existing)

    # ② 如 Simulator 已在内存，同步追加（立即生效）
    sim = _SIMULATORS.get(world_id)
    if sim is None:
        # 兜底：按 world.id / world.name 匹配
        for s in _SIMULATORS.values():
            if s.world.id == world_id or s.world.name == world_id:
                sim = s
                break
    if sim is not None:
        sim.directives = getattr(sim, "directives", [])
        sim.directives.append(directive)
        return {"status": "queued", "world_id": world_id, "directive_type": dtype}

    return {
        "status": "queued",
        "world_id": world_id,
        "directive_type": dtype,
        "note": "will apply on next tick (persisted to directives.yaml)",
    }
