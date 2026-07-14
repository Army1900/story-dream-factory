import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.persistence.world_store import WorldStore


@pytest.fixture()
def dir_client(worlds_tmp, monkeypatch):
    store = WorldStore()
    store.save_world(
        worlds_tmp / "w-d",
        {
            "id": "w-d",
            "name": "测试",
            "setting": "测试",
            "clock_tick": 0,
            "characters": [
                {
                    "id": "c-d",
                    "name": "艾伦",
                    "state": {"location_id": "酒馆", "health": 100},
                }
            ],
        },
    )

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="叙述")
    mock_llm.complete_json = AsyncMock(
        return_value={
            "intent": "等待",
            "action_type": "wait",
            "target": "",
            "expectation": "",
            "dialogue": "",
        }
    )
    monkeypatch.setattr("app.api.simulation._get_llm", lambda: mock_llm)

    with TestClient(app) as c:
        yield c

    from app.api.simulation import _SIMULATORS

    _SIMULATORS.clear()


def test_inject_event(dir_client):
    resp = dir_client.post(
        "/worlds/w-d/director/inject",
        json={"type": "inject_event", "payload": {"description": "暴风雨来了"}, "target": ""},
    )
    assert resp.status_code == 200
    assert "queued" in resp.json()["status"]


def test_set_goal(dir_client):
    resp = dir_client.post(
        "/worlds/w-d/director/inject",
        json={"type": "set_goal", "payload": {"goal": "复仇"}, "target": "艾伦"},
    )
    assert resp.status_code == 200


def test_modify_world(dir_client):
    resp = dir_client.post(
        "/worlds/w-d/director/inject",
        json={"type": "modify_world", "payload": {"key": "state_flags", "value": {"war": True}}, "target": ""},
    )
    assert resp.status_code == 200


def test_directive_appears_in_next_step(dir_client):
    dir_client.post(
        "/worlds/w-d/director/inject",
        json={"type": "inject_event", "payload": {"description": "旅人到来"}, "target": ""},
    )
    dir_client.post("/worlds/w-d/simulate/start")
    resp = dir_client.post("/worlds/w-d/simulate/step")
    assert resp.status_code == 200
    assert "events" in resp.json()


def test_directive_persisted_to_file(dir_client, worlds_tmp):
    """导演指令应落盘到 directives.yaml。"""
    dir_client.post(
        "/worlds/w-d/director/inject",
        json={"type": "inject_event", "payload": {"description": "暴风雨"}, "target": ""},
    )
    store = WorldStore()
    directives = store.load_directives(worlds_tmp / "w-d")
    assert len(directives) == 1
    assert directives[0]["type"] == "inject_event"
