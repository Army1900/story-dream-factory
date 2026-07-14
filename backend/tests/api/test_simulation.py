import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_session, set_engine

@pytest.fixture()
def sim_client(tmp_path, monkeypatch):
    from sqlmodel import Session, SQLModel, create_engine
    from app.models.world import World
    from app.models.character import Character
    from app.persistence.repository import WorldRepository, CharacterRepository

    engine = create_engine(f"sqlite:///{tmp_path/'sim.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    set_engine(engine)

    # 种子数据
    with Session(engine) as s:
        repo_w = WorldRepository(s)
        world = repo_w.create(World(id="w-sim", name="测试世界", setting="测试"))
        repo_c = CharacterRepository(s)
        repo_c.create(Character(id="c-sim", world_id="w-sim", name="艾伦",
                                personality={"n":"0.8"}, backstory="骑士",
                                goals={"short_term":"复仇"}, state={"location_id":"酒馆","mood":"怒"}))

    def _gs():
        with Session(engine) as s:
            yield s
    app.dependency_overrides[get_session] = _gs

    # mock LLM
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="叙述。")
    mock_llm.complete_json = AsyncMock(return_value={"intent":"等待","action_type":"wait","target":"","expectation":"","dialogue":""})
    monkeypatch.setattr("app.api.simulation._get_llm", lambda: mock_llm)

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


def test_start_simulation(sim_client):
    resp = sim_client.post("/worlds/w-sim/simulate/start")
    assert resp.status_code == 200
    assert "sim_id" in resp.json()

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
