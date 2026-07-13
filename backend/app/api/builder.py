from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_session
from app.models.character import Character
from app.models.location import Location
from app.models.world import World
from app.persistence.repository import (
    CharacterRepository,
    LocationRepository,
    WorldRepository,
)
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
def finalize_session(sid: str, session_db: Session = Depends(get_session)):
    session = _SESSIONS.get(sid)
    if not session:
        return {"error": "session not found"}

    # 健康检查
    health = run_health_check(session.collected)

    # 组装 World 对象
    collected = session.collected
    world = World(
        name=session.world_name or "新世界",
        vision=str(collected.get("vision", {}).get("type", "")),
        setting=str(collected.get("setting", "")),
        rules=collected.get("rules", []),
        visual_style=collected.get("visual_style", {}),
        initial_state=collected.get("inciting", {}),
    )
    repo = WorldRepository(session_db)
    repo.create(world)

    # 角色
    char_repo = CharacterRepository(session_db)
    for ch in collected.get("characters", []):
        if isinstance(ch, dict):
            char_repo.create(
                Character(
                    world_id=world.id,
                    name=ch.get("name", ""),
                    archetype=ch.get("archetype", ""),
                    goals=ch.get("goals", {}),
                    personality=ch.get("personality", {}),
                )
            )

    # 地点
    loc_repo = LocationRepository(session_db)
    for loc in collected.get("locations", []):
        if isinstance(loc, (str, dict)):
            name = loc if isinstance(loc, str) else loc.get("name", "")
            if name:
                loc_repo.create(Location(world_id=world.id, name=name))

    return {
        "world_id": world.id,
        "health": {
            "passed": health.passed,
            "errors": health.errors,
            "warnings": health.warnings,
            "checklist": health.checklist,
        },
    }
