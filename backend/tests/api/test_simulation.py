import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.persistence.world_store import WorldStore


@pytest.fixture()
def sim_client(worlds_tmp, monkeypatch):
    # 种子：写一个世界文件
    store = WorldStore()
    store.save_world(
        worlds_tmp / "w-sim",
        {
            "id": "w-sim",
            "name": "测试世界",
            "setting": "测试",
            "clock_tick": 0,
            "characters": [
                {
                    "id": "c-sim",
                    "name": "艾伦",
                    "personality": {"n": "0.8"},
                    "backstory": "骑士",
                    "goals": {"short_term": "复仇"},
                    "state": {"location_id": "酒馆", "mood": "怒"},
                }
            ],
        },
    )

    # mock LLM
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="叙述。")
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

    # 清空内存中的 simulator（隔离测试）
    from app.api.simulation import _SIMULATORS

    _SIMULATORS.clear()


def test_start_simulation(sim_client):
    resp = sim_client.post("/worlds/w-sim/simulate/start")
    assert resp.status_code == 200
    data = resp.json()
    assert "sim_id" in data
    assert data["world"] == "测试世界"
    assert "艾伦" in data["characters"]


def test_step_simulation(sim_client):
    sim_client.post("/worlds/w-sim/simulate/start")
    resp = sim_client.post("/worlds/w-sim/simulate/step")
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert len(data["events"]) >= 1


def test_simulation_status(sim_client):
    sim_client.post("/worlds/w-sim/simulate/start")
    sim_client.post("/worlds/w-sim/simulate/step")
    resp = sim_client.get("/worlds/w-sim/simulate/status")
    assert resp.status_code == 200
    assert resp.json()["tick"] >= 1
    assert resp.json()["total_events"] >= 1


def test_start_missing_world(sim_client):
    resp = sim_client.post("/worlds/no-such/simulate/start")
    assert resp.status_code == 200
    assert "error" in resp.json()


def test_step_persists_to_file(sim_client, worlds_tmp):
    """端到端验证：step 后 events/world 落盘。"""
    sim_client.post("/worlds/w-sim/simulate/start")
    sim_client.post("/worlds/w-sim/simulate/step")
    world_dir = worlds_tmp / "w-sim"
    assert (world_dir / "events").exists()
    assert (world_dir / "world.yaml").exists()
    # clock_tick 应已推进
    store = WorldStore()
    wd = store.load_world(world_dir)
    assert wd["clock_tick"] >= 1
