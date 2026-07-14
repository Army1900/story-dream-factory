import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture()
def ws_client(tmp_path, monkeypatch):
    from sqlmodel import Session, SQLModel, create_engine
    from app.models.world import World
    from app.models.character import Character
    from app.persistence.repository import WorldRepository, CharacterRepository
    from app.api.deps import get_session, set_engine
    from unittest.mock import AsyncMock, MagicMock
    engine = create_engine(f"sqlite:///{tmp_path/'ws.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    set_engine(engine)
    with Session(engine) as s:
        WorldRepository(s).create(World(id="w-ws", name="WS测试", setting="测试", clock_tick=0))
        CharacterRepository(s).create(Character(id="c-ws", world_id="w-ws", name="艾伦", state={"location_id":"酒馆","health":100}))
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="实时叙述")
    mock_llm.complete_json = AsyncMock(return_value={"intent":"等待","action_type":"wait","target":"","expectation":"","dialogue":""})
    monkeypatch.setattr("app.api.simulation._get_llm", lambda: mock_llm)
    def _gs():
        with Session(engine) as s:
            yield s
    app.dependency_overrides[get_session] = _gs
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()

def test_websocket_connect(ws_client):
    ws_client.post("/worlds/w-ws/simulate/start")
    with ws_client.websocket_connect("/worlds/w-ws/ws") as ws:
        # 发 step 指令
        ws.send_json({"action": "step"})
        # 接收事件
        data = ws.receive_json()
        assert "events" in data or "tick" in data

def test_websocket_disconnect(ws_client):
    ws_client.post("/worlds/w-ws/simulate/start")
    with ws_client.websocket_connect("/worlds/w-ws/ws") as ws:
        ws.send_json({"action": "disconnect"})
