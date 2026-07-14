import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.persistence.world_store import WorldStore


@pytest.fixture()
def ws_client(worlds_tmp, monkeypatch):
    store = WorldStore()
    store.save_world(
        worlds_tmp / "w-ws",
        {
            "id": "w-ws",
            "name": "WS测试",
            "setting": "测试",
            "clock_tick": 0,
            "characters": [
                {
                    "id": "c-ws",
                    "name": "艾伦",
                    "state": {"location_id": "酒馆", "health": 100},
                }
            ],
        },
    )

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="实时叙述")
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


def test_websocket_connect(ws_client):
    ws_client.post("/worlds/w-ws/simulate/start")
    with ws_client.websocket_connect("/worlds/w-ws/ws") as ws:
        ws.send_json({"action": "step"})
        data = ws.receive_json()
        assert "events" in data or "tick" in data


def test_websocket_step_without_start_loads_from_file(ws_client):
    """重启后场景：未调用 /start，直接 ws step 应能从文件加载。"""
    with ws_client.websocket_connect("/worlds/w-ws/ws") as ws:
        ws.send_json({"action": "step"})
        data = ws.receive_json()
        assert "events" in data


def test_websocket_status(ws_client):
    ws_client.post("/worlds/w-ws/simulate/start")
    with ws_client.websocket_connect("/worlds/w-ws/ws") as ws:
        ws.send_json({"action": "status"})
        data = ws.receive_json()
        assert "tick" in data


def test_websocket_disconnect(ws_client):
    ws_client.post("/worlds/w-ws/simulate/start")
    with ws_client.websocket_connect("/worlds/w-ws/ws") as ws:
        ws.send_json({"action": "disconnect"})
