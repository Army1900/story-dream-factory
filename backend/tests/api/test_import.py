from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import app
from app.persistence.world_store import WorldStore


@pytest.fixture()
def mock_llm(monkeypatch):
    """Mock LLM 网关，避免真实 API 调用；测试内可改写 complete 返回值。"""
    mock = MagicMock()
    mock.complete = AsyncMock(return_value="name: 临时")
    monkeypatch.setattr("app.api.import_world._get_llm", lambda: mock)
    return mock


@pytest.fixture()
def import_client(mock_llm, worlds_tmp):
    """TestClient（已 patch LLM + worlds_dir 指向临时目录）。"""
    with TestClient(app) as c:
        yield c


def test_import_creates_world(import_client, mock_llm, worlds_tmp):
    """LLM 返回合法 YAML → 世界文件被创建并含提取内容。"""
    extracted_yaml = (
        "name: 机械之城\n"
        "vision: 蒸汽朋克\n"
        "setting: 一座齿轮驱动的悬浮都市\n"
        "rules:\n"
        "  - 重力每 12 小时反转一次\n"
        "characters:\n"
        "  - name: 艾琳\n"
        "    archetype: 机械师\n"
        "    backstory: 孤儿出身\n"
        "locations:\n"
        "  - name: 钟塔广场\n"
        "    neighbors: [齿轮巷]\n"
    )
    mock_llm.complete = AsyncMock(return_value=extracted_yaml)

    resp = import_client.post(
        "/worlds/import",
        json={"text": "（小说片段，内容略）", "world_name": ""},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["world_name"] == "机械之城"
    assert data["world_id"] == "机械之城"

    # 落盘校验
    world_yaml = worlds_tmp / "机械之城" / "world.yaml"
    assert world_yaml.exists()
    saved = yaml.safe_load(world_yaml.read_text(encoding="utf-8"))
    assert saved["name"] == "机械之城"
    assert saved["vision"] == "蒸汽朋克"
    assert len(saved["characters"]) == 1
    assert saved["characters"][0]["name"] == "艾琳"
    # schema 补齐字段
    assert saved["clock_tick"] == 0
    assert saved["rules"] == ["重力每 12 小时反转一次"]

    # 返回结构也应含补齐字段与提取内容
    assert data["extracted"]["locations"][0]["name"] == "钟塔广场"


def test_import_fallback_on_parse_error(import_client, mock_llm, worlds_tmp):
    """LLM 返回非 YAML 垃圾 → 降级创建最小世界，不报错。"""
    mock_llm.complete = AsyncMock(return_value="这不是有效的 YAML [[[ }}")

    resp = import_client.post(
        "/worlds/import",
        json={"text": "一段杂乱的文本 123", "world_name": "降级世界"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # 降级时使用 hint_name
    assert data["world_name"] == "降级世界"
    assert data["world_id"] == "降级世界"

    # 落盘校验：最小结构
    saved = WorldStore().load_world(worlds_tmp / "降级世界")
    assert saved is not None
    assert saved["name"] == "降级世界"
    assert saved["characters"] == []
    assert saved["clock_tick"] == 0
    # setting 取原文前 200 字
    assert saved["setting"].startswith("一段杂乱的文本")


def test_import_preserves_provided_name(import_client, mock_llm, worlds_tmp):
    """用户提供了 world_name 且 LLM 未返回 name → 使用用户提供的名字。"""
    # LLM 返回内容不含 name 字段
    extracted_yaml = (
        "vision: 黑暗奇幻\n"
        "setting: 被诅咒的王国\n"
    )
    mock_llm.complete = AsyncMock(return_value=extracted_yaml)

    resp = import_client.post(
        "/worlds/import",
        json={"text": "...", "world_name": "用户指定名"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["world_name"] == "用户指定名"
    assert data["world_id"] == "用户指定名"

    saved = WorldStore().load_world(worlds_tmp / "用户指定名")
    assert saved is not None
    assert saved["name"] == "用户指定名"
    # 其余提取内容仍保留
    assert saved["vision"] == "黑暗奇幻"


def test_import_calls_llm_once(import_client, mock_llm):
    """确认走的是 LLM 提取路径（complete 被调用一次）。"""
    mock_llm.complete = AsyncMock(return_value="name: x")
    import_client.post("/worlds/import", json={"text": "abc"})
    assert mock_llm.complete.await_count == 1
