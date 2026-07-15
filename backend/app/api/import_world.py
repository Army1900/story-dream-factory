"""文本导入世界构建模式。

用户粘贴一段文本（小说片段/设定文档/几段描述），LLM 自动提取结构化世界设定，
落盘为 ``worlds/{name}/world.yaml``。
"""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.persistence.world_store import WorldStore

router = APIRouter(prefix="/worlds/import", tags=["import"])


class ImportRequest(BaseModel):
    text: str  # 用户粘贴的文本
    world_name: str = ""  # 可选世界名（空则 LLM 提取）


class ImportResponse(BaseModel):
    world_name: str
    extracted: dict  # 结构化的世界数据
    world_id: str  # 创建后的世界 ID（目录名）


def _get_llm():
    """获取 LLM 网关（延迟创建；与 builder/simulation 一致）。"""
    from app.llm.config import LLMRoutingConfig, TierConfig
    from app.llm.gateway import LLMGateway

    settings = get_settings()
    routing = LLMRoutingConfig(
        tiers={"tier1": TierConfig(model=settings.llm_tier1_model)},
        default_tier="tier1",
    )
    return LLMGateway(routing=routing, api_key=settings.zhipu_api_key)


@router.post("", response_model=ImportResponse)
async def import_from_text(req: ImportRequest):
    """从文本提取世界设定并创建世界。"""
    # 1. 用 LLM 从文本提取结构化世界数据
    extracted = await _extract_world_from_text(req.text, req.world_name)
    # 2. 用 WorldStore 创建世界
    settings = get_settings()
    name = extracted.get("name", req.world_name or "导入的世界")
    world_dir = Path(settings.worlds_dir) / name
    WorldStore().save_world(world_dir, extracted)
    return ImportResponse(world_name=name, extracted=extracted, world_id=name)


async def _extract_world_from_text(text: str, hint_name: str = "") -> dict:
    """用 LLM 从文本提取结构化世界设定，解析失败时降级为最小结构。"""
    llm = _get_llm()

    prompt = f"""分析以下文本，提取一个故事世界设定。输出 YAML 格式的结构化数据。

文本：
{text[:8000]}

请提取以下维度（如果文本中有）：
- name: 世界名（{hint_name or "从文本推断"}）
- vision: 愿景/基调
- setting: 世界设定描述
- rules: 世界规则列表
- visual_style: 视觉风格（art_style, palette）
- characters: 角色列表（name, archetype, personality, backstory, goals, state）
- locations: 地点列表（name, neighbors）

只输出 YAML，不要解释。"""

    result = await llm.complete(
        messages=[
            {
                "role": "system",
                "content": "你是世界构建专家。从文本提取结构化世界设定。",
            },
            {"role": "user", "content": prompt},
        ]
    )

    # 解析 LLM 返回的 YAML
    try:
        data = yaml.safe_load(result)
        if isinstance(data, dict):
            return _normalize_extracted(data, hint_name)
    except Exception:
        pass

    # 降级：返回最小结构
    return _fallback_extracted(text, hint_name)


def _normalize_extracted(data: dict, hint_name: str = "") -> dict:
    """补齐 world.yaml schema 必要字段，保证落盘后可被 simulation 加载。"""
    name = data.get("name") or hint_name or "导入的世界"
    data["id"] = data.get("id", name)
    data["name"] = name
    data.setdefault("vision", "")
    data.setdefault("setting", "")
    data.setdefault("clock_tick", 0)
    data.setdefault("clock_date", "")
    data.setdefault("rules", [])
    data.setdefault("characters", [])
    data.setdefault("locations", [])
    data.setdefault("relationships", [])
    data.setdefault("state_flags", {})
    data.setdefault("initial_state", {})
    data.setdefault("visual_style", {})
    return data


def _fallback_extracted(text: str, hint_name: str = "") -> dict:
    """LLM 解析失败时的最小可用世界结构。"""
    return {
        "id": hint_name or "导入的世界",
        "name": hint_name or "导入的世界",
        "vision": "从文本导入",
        "setting": text[:200],
        "rules": [],
        "characters": [],
        "locations": [],
        "relationships": [],
        "clock_tick": 0,
        "clock_date": "",
        "state_flags": {},
        "initial_state": {},
        "visual_style": {},
    }
