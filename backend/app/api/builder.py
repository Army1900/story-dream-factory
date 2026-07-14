from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter

from app.config import get_settings
from app.persistence.world_store import WorldStore
from app.worldbuilder.conversation import ConversationService
from app.worldbuilder.health_check import run_health_check
from app.worldbuilder.session import BuilderSession
from app.worldbuilder.stages import STAGES
from app.worldbuilder.templates import BUILTIN_TEMPLATES

router = APIRouter(prefix="/worlds/builder", tags=["world-builder"])

# 内存中的 session 存储（MVP；后续可持久化到 DB）
_SESSIONS: dict[str, BuilderSession] = {}


def _get_llm():
    """获取 LLM 网关（MVP：延迟创建）。"""
    from app.config import get_settings
    from app.llm.config import LLMRoutingConfig, TierConfig
    from app.llm.gateway import LLMGateway

    settings = get_settings()
    routing = LLMRoutingConfig(
        tiers={"tier1": TierConfig(model=settings.llm_tier1_model)},
        default_tier="tier1",
    )
    return LLMGateway(routing=routing, api_key=settings.zhipu_api_key)


@router.post("/session")
def create_session(payload: dict):
    tpl_idx = payload.get("template_index")
    template = (
        BUILTIN_TEMPLATES[tpl_idx]
        if tpl_idx is not None and tpl_idx < len(BUILTIN_TEMPLATES)
        else None
    )
    session = BuilderSession(template=template)
    sid = str(uuid.uuid4())
    _SESSIONS[sid] = session
    stage = STAGES[session.current_stage]
    return {
        "session_id": sid,
        "stage": session.current_stage,
        "stage_title": stage["title"],
        "prompt_hint": stage["prompt_hint"],
        "checklist": stage["checklist"],
    }


@router.post("/session/{sid}/message")
async def send_message(sid: str, payload: dict):
    session = _SESSIONS.get(sid)
    if not session:
        return {"error": "session not found"}
    msg = payload.get("message", "")
    llm = _get_llm()
    svc = ConversationService(llm)
    reply = await svc.process_message(session, msg)
    stage = STAGES[session.current_stage]
    return {
        "reply": reply,
        "stage": session.current_stage,
        "stage_title": stage["title"],
        "checklist_progress": session.checklist_progress().get(
            session.current_stage, {}
        ),
    }


@router.get("/session/{sid}/progress")
def get_progress(sid: str):
    session = _SESSIONS.get(sid)
    if not session:
        return {"error": "session not found"}
    return {
        "stage": session.current_stage,
        "collected": session.collected,
        "checklist": session.checklist_progress(),
        "messages": session.messages[-5:],
    }


@router.post("/session/{sid}/go-back")
def go_back(sid: str):
    session = _SESSIONS.get(sid)
    if not session:
        return {"error": "session not found"}
    session.go_back()
    stage = STAGES[session.current_stage]
    return {"stage": session.current_stage, "stage_title": stage["title"]}


@router.post("/session/{sid}/finalize")
def finalize_session(sid: str):
    session = _SESSIONS.get(sid)
    if not session:
        return {"error": "session not found"}

    # 健康检查
    health = run_health_check(session.collected)

    # 组装 world_dict（world.yaml schema）
    collected = session.collected
    name = session.world_name or "新世界"

    characters: list[dict] = []
    for ch in collected.get("characters", []):
        if not isinstance(ch, dict):
            continue
        cname = ch.get("name", "")
        characters.append(
            {
                "id": ch.get("id", cname),
                "name": cname,
                "archetype": ch.get("archetype", ""),
                "personality": ch.get("personality", {}) or {},
                "backstory": ch.get("backstory", ""),
                "goals": ch.get("goals", {}) or {},
                "state": ch.get("state", {}) or {},
            }
        )

    locations: list[dict] = []
    for loc in collected.get("locations", []):
        loc_name = loc if isinstance(loc, str) else loc.get("name", "")
        if loc_name:
            entry = {"id": loc_name, "name": loc_name}
            if isinstance(loc, dict):
                entry.update(
                    {
                        "description": loc.get("description", ""),
                        "neighbors": loc.get("neighbors", []) or [],
                        "occupants": loc.get("occupants", []) or [],
                        "resources": loc.get("resources", []) or [],
                    }
                )
            locations.append(entry)

    world_dict = {
        "id": name,
        "name": name,
        "vision": str(collected.get("vision", {}).get("type", "")),
        "setting": str(collected.get("setting", "")),
        "rules": collected.get("rules", []) or [],
        "visual_style": collected.get("visual_style", {}) or {},
        "clock_tick": 0,
        "clock_date": "",
        "state_flags": {},
        "initial_state": collected.get("inciting", {}) or {},
        "characters": characters,
        "locations": locations,
        "relationships": [],
    }

    world_dir = Path(get_settings().worlds_dir) / name
    WorldStore().save_world(world_dir, world_dict)

    return {
        "world_id": name,
        "health": {
            "passed": health.passed,
            "errors": health.errors,
            "warnings": health.warnings,
            "checklist": health.checklist,
        },
    }
