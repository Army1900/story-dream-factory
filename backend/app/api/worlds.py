from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.persistence.world_store import WorldStore

router = APIRouter(prefix="/worlds", tags=["worlds"])

_store = WorldStore()


def _world_dir(world_name: str) -> Path:
    """世界名 → worlds/{world_name} 目录路径。"""
    return Path(get_settings().worlds_dir) / world_name


def _assemble_world_dict(payload: dict) -> dict:
    """把 POST body 组装成 world.yaml schema。

    支持两种 body 形态：
    - 扁平：{"name": "...", "vision": "...", "characters": [...]}
    - 嵌套：{"world": {...}, "characters": [...], "locations": [...]}
    """
    inner = payload.get("world", {}) if isinstance(payload.get("world"), dict) else {}
    name = payload.get("name") or inner.get("name") or ""
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    return {
        "id": payload.get("id", inner.get("id", name)),
        "name": name,
        "vision": payload.get("vision", inner.get("vision", "")),
        "setting": payload.get("setting", inner.get("setting", "")),
        "rules": payload.get("rules", inner.get("rules", [])) or [],
        "visual_style": payload.get("visual_style", inner.get("visual_style", {})) or {},
        "clock_tick": payload.get("clock_tick", inner.get("clock_tick", 0)) or 0,
        "clock_date": payload.get("clock_date", inner.get("clock_date", "")) or "",
        "state_flags": payload.get("state_flags", inner.get("state_flags", {})) or {},
        "initial_state": payload.get("initial_state", inner.get("initial_state", {})) or {},
        "characters": payload.get("characters", inner.get("characters", [])) or [],
        "locations": payload.get("locations", inner.get("locations", [])) or [],
        "relationships": payload.get("relationships", inner.get("relationships", [])) or [],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_world(payload: dict) -> dict:
    world_dict = _assemble_world_dict(payload)
    _store.save_world(_world_dir(world_dict["name"]), world_dict)
    return world_dict


@router.get("")
def list_worlds() -> list[dict]:
    """返回所有世界的摘要列表。"""
    summaries: list[dict] = []
    for name in _store.list_worlds(get_settings().worlds_dir):
        wd = _store.load_world(_world_dir(name)) or {}
        summaries.append(
            {
                "name": name,
                "id": wd.get("id", name),
                "vision": wd.get("vision", ""),
                "clock_tick": wd.get("clock_tick", 0),
                "rules_count": len(wd.get("rules", []) or []),
            }
        )
    return summaries


@router.get("/{world_id}")
def get_world(world_id: str) -> dict:
    wd = _store.load_world(_world_dir(world_id))
    if wd is None:
        raise HTTPException(status_code=404, detail="World not found")
    return wd


@router.delete("/{world_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_world(world_id: str) -> None:
    _store.delete_world(_world_dir(world_id))
