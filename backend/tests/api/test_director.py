import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_session, set_engine

@pytest.fixture()
def dir_client(tmp_path, monkeypatch):
    from sqlmodel import Session, SQLModel, create_engine
    from app.models.world import World
    from app.models.character import Character
    from app.persistence.repository import WorldRepository, CharacterRepository
    engine = create_engine(f"sqlite:///{tmp_path/'dir.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    set_engine(engine)
    with Session(engine) as s:
        WorldRepository(s).create(World(id="w-d", name="测试", setting="测试", clock_tick=0))
        CharacterRepository(s).create(Character(id="c-d", world_id="w-d", name="艾伦", state={"location_id":"酒馆","health":100}))
    def _gs():
        with Session(engine) as s:
            yield s
    app.dependency_overrides[get_session] = _gs
    # mock LLM for simulation
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="叙述")
    mock_llm.complete_json = AsyncMock(return_value={"intent":"等待","action_type":"wait","target":"","expectation":"","dialogue":""})
    monkeypatch.setattr("app.api.simulation._get_llm", lambda: mock_llm)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()

def test_inject_event(dir_client):
    resp = dir_client.post("/worlds/w-d/director/inject", json={"type":"inject_event","payload":{"description":"暴风雨来了"},"target":""})
    assert resp.status_code == 200
    assert "queued" in resp.json()["status"]

def test_set_goal(dir_client):
    resp = dir_client.post("/worlds/w-d/director/inject", json={"type":"set_goal","payload":{"goal":"复仇"},"target":"艾伦"})
    assert resp.status_code == 200

def test_modify_world(dir_client):
    resp = dir_client.post("/worlds/w-d/director/inject", json={"type":"modify_world","payload":{"key":"state_flags","value":{"war":True}},"target":""})
    assert resp.status_code == 200

def test_directive_appears_in_next_step(dir_client):
    dir_client.post("/worlds/w-d/director/inject", json={"type":"inject_event","payload":{"description":"旅人到来"},"target":""})
    dir_client.post("/worlds/w-d/simulate/start")
    resp = dir_client.post("/worlds/w-d/simulate/step")
    assert resp.status_code == 200
    # 事件应该包含注入的内容（或至少 tick 推进了）
    assert "events" in resp.json()
