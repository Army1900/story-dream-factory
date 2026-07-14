from fastapi.testclient import TestClient


def test_create_builder_session(client_fixture):
    resp = client_fixture.post("/worlds/builder/session", json={"template_index": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["stage"] == "vision"
    assert data["stage_title"] == "愿景"
    assert data["prompt_hint"]
    assert isinstance(data["checklist"], list) and len(data["checklist"]) > 0


def test_create_builder_session_no_template(client_fixture):
    resp = client_fixture.post("/worlds/builder/session", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["stage"] == "vision"


def test_send_message(client_fixture, mock_llm):
    # 先创建 session
    resp = client_fixture.post("/worlds/builder/session", json={"template_index": 0})
    sid = resp.json()["session_id"]
    # 发消息
    resp = client_fixture.post(
        f"/worlds/builder/session/{sid}/message", json={"message": "黑暗奇幻"}
    )
    assert resp.status_code == 200
    assert "reply" in resp.json()
    assert resp.json()["reply"]  # 非空
    # mock_llm.complete 被调用过一次
    assert mock_llm.complete.await_count == 1


def test_get_progress(client_fixture):
    resp = client_fixture.post("/worlds/builder/session", json={})
    sid = resp.json()["session_id"]
    resp = client_fixture.get(f"/worlds/builder/session/{sid}/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert "stage" in data
    assert "checklist" in data
    assert "collected" in data


def test_go_back(client_fixture):
    resp = client_fixture.post("/worlds/builder/session", json={})
    sid = resp.json()["session_id"]
    # 推进到 setting
    client_fixture.post(
        f"/worlds/builder/session/{sid}/message", json={"message": "完成，下一步"}
    )
    assert client_fixture.get(
        f"/worlds/builder/session/{sid}/progress"
    ).json()["stage"] == "setting"
    # 回退到 vision
    resp = client_fixture.post(f"/worlds/builder/session/{sid}/go-back")
    assert resp.status_code == 200
    assert resp.json()["stage"] == "vision"
    assert resp.json()["stage_title"] == "愿景"


def test_finalize(client_fixture, mock_llm):
    resp = client_fixture.post("/worlds/builder/session", json={"template_index": 0})
    sid = resp.json()["session_id"]
    resp = client_fixture.post(f"/worlds/builder/session/{sid}/finalize")
    assert resp.status_code == 200
    data = resp.json()
    assert "world_id" in data
    assert "health" in data
    assert "passed" in data["health"]
    assert isinstance(data["health"]["checklist"], list)


def test_finalize_missing_session_returns_error(client_fixture):
    resp = client_fixture.post("/worlds/builder/session/no-such-id/finalize")
    # 端点返回 {"error": ...}（计划语义）——验证 error 字段
    assert resp.status_code == 200
    assert resp.json().get("error") == "session not found"
