import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.persistence.world_store import WorldStore


@pytest.fixture()
def client(worlds_tmp):
    with TestClient(app) as c:
        yield c


def test_create_and_get_world(client):
    resp = client.post("/worlds", json={"name": "艾尔德兰", "vision": "v"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "艾尔德兰"
    assert body["id"] == "艾尔德兰"  # world_id = 世界名（目录名）

    resp = client.get("/worlds/艾尔德兰")
    assert resp.status_code == 200
    assert resp.json()["vision"] == "v"


def test_list_worlds(client):
    client.post("/worlds", json={"name": "a", "rules": ["r1", "r2"]})
    client.post("/worlds", json={"name": "b"})
    resp = client.get("/worlds")
    assert resp.status_code == 200
    names = [w["name"] for w in resp.json()]
    assert names == ["a", "b"]
    # 摘要字段
    a = next(w for w in resp.json() if w["name"] == "a")
    assert a["rules_count"] == 2


def test_delete_world(client):
    client.post("/worlds", json={"name": "a"})
    resp = client.delete("/worlds/a")
    assert resp.status_code == 204
    assert client.get("/worlds/a").status_code == 404


def test_get_missing_world_404(client):
    assert client.get("/worlds/nope").status_code == 404


def test_create_with_nested_characters_and_locations(client, worlds_tmp):
    payload = {
        "name": "nested",
        "characters": [{"name": "艾伦", "archetype": "骑士"}],
        "locations": [{"name": "酒馆"}],
    }
    resp = client.post("/worlds", json=payload)
    assert resp.status_code == 201
    wd = resp.json()
    assert len(wd["characters"]) == 1
    assert wd["characters"][0]["name"] == "艾伦"
    assert len(wd["locations"]) == 1
    # 确认落盘
    assert (worlds_tmp / "nested" / "world.yaml").exists()
