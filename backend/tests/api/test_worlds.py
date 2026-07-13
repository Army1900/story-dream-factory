import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

# 注册模型
import app.models.world  # noqa: F401
from app.api.deps import get_session
from app.main import app, set_engine


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 't.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    set_engine(engine)

    def _get_session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


def test_create_and_get_world(client):
    resp = client.post("/worlds", json={"name": "艾尔德兰", "vision": "v"})
    assert resp.status_code == 201
    wid = resp.json()["id"]
    assert resp.json()["name"] == "艾尔德兰"

    resp = client.get(f"/worlds/{wid}")
    assert resp.status_code == 200
    assert resp.json()["vision"] == "v"


def test_list_worlds(client):
    client.post("/worlds", json={"name": "a"})
    client.post("/worlds", json={"name": "b"})
    resp = client.get("/worlds")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_delete_world(client):
    resp = client.post("/worlds", json={"name": "a"})
    wid = resp.json()["id"]
    resp = client.delete(f"/worlds/{wid}")
    assert resp.status_code == 204
    assert client.get(f"/worlds/{wid}").status_code == 404


def test_get_missing_world_404(client):
    assert client.get("/worlds/nope").status_code == 404
