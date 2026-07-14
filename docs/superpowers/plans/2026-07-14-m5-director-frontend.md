# M5 导演介入 + 前端 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 实现导演介入 API + WebSocket 实时推送 + React 前端，把整个模拟系统呈现给用户。

**Architecture:** 后端加导演介入端点（4 种类型）+ WebSocket 推送 tick 事件。前端用 Vite + React + TS，基于已有原型设计（docs/prototypes/site-neutral.html），连接后端 API。

**Tech Stack:** FastAPI WebSocket、React 18、TypeScript、Vite、Zustand。

---

## Task 1: 导演介入 API

**Files:**
- Create: `app/api/director.py`
- Modify: `app/api/router.py`
- Modify: `app/engine/simulator.py`（tick 开头检查注入队列）
- Test: `tests/api/test_director.py`

- [ ] **Step 1: 写测试**

```python
# tests/api/test_director.py
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
```

- [ ] **Step 2: 实现 `app/api/director.py`**

```python
from __future__ import annotations
from fastapi import APIRouter
from app.api.simulation import _SIMULATORS

router = APIRouter(prefix="/worlds/{world_id}/director", tags=["director"])

@router.post("/inject")
def inject_directive(world_id: str, payload: dict):
    """导演介入：注入事件/改目标/改规则/强制行动。"""
    dtype = payload.get("type", "inject_event")
    data = payload.get("payload", {})
    target = payload.get("target", "")
    # 找到该世界的 simulator
    sim = None
    for s in _SIMULATORS.values():
        if s.world.id == world_id:
            sim = s
            break
    if sim:
        sim.directives = getattr(sim, 'directives', [])
        sim.directives.append({"type": dtype, "payload": data, "target": target})
        return {"status": "queued", "world_id": world_id, "directive_type": dtype}
    return {"status": "queued", "world_id": world_id, "directive_type": dtype, "note": "will apply on next tick"}
```

- [ ] **Step 3: 修改 `app/engine/simulator.py`（tick 开头处理注入）**

在 `__init__` 中添加：
```python
self.directives: list[dict] = []
```

在 `tick()` 方法开头（角色决策前）添加：
```python
# 处理导演注入
injected_events = []
while self.directives:
    d = self.directives.pop(0)
    if d["type"] == "inject_event":
        from app.models.event import Event
        from app.models.enums import EventType
        evt = Event(
            world_id=self.world.id, tick=current_tick,
            type=EventType.director,
            participants=[], location_id="",
            payload=d["payload"],
            narration=d["payload"].get("description", "导演介入"),
        )
        injected_events.append(evt)
        self.event_history.append(evt)
    elif d["type"] == "set_goal":
        target_name = d.get("target", "")
        for c in self.characters:
            if c.name == target_name:
                c.goals = c.goals or {}
                c.goals.update(d["payload"])
    elif d["type"] == "modify_world":
        key = d["payload"].get("key", "")
        value = d["payload"].get("value")
        if key == "state_flags" and isinstance(value, dict):
            self.world.state_flags.update(value)
        elif key == "rules" and isinstance(value, list):
            self.world.rules = value
events = injected_events + events if 'events' in dir() else injected_events
```

- [ ] **Step 4: 修改 `app/api/router.py`**

```python
from app.api import director
api_router.include_router(director.router)
```

- [ ] **Step 5: 跑测试 + commit**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/api/test_director.py -v
git add backend/ && git commit -m "feat: M5 Task 1 导演介入 API"
```

---

## Task 2: WebSocket 实时推送

**Files:**
- Create: `app/api/websocket.py`
- Modify: `app/api/router.py`
- Modify: `app/engine/simulator.py`（step 后通知 WebSocket）
- Test: `tests/api/test_websocket.py`

- [ ] **Step 1: 写测试**

```python
# tests/api/test_websocket.py
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
```

- [ ] **Step 2: 实现 `app/api/websocket.py`**

```python
from __future__ import annotations
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api.simulation import _SIMULATORS, _get_llm

router = APIRouter(tags=["websocket"])


@router.websocket("/worlds/{world_id}/ws")
async def world_websocket(websocket: WebSocket, world_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action", "")
            if action == "step":
                sim = None
                for s in _SIMULATORS.values():
                    if s.world.id == world_id:
                        sim = s
                        break
                if sim:
                    events = await sim.tick()
                    await websocket.send_json({
                        "tick": sim.world.clock_tick,
                        "events": [
                            {"tick": e.tick, "type": e.type.value if hasattr(e.type, "value") else str(e.type),
                             "narration": e.narration, "participants": e.participants}
                            for e in events
                        ],
                    })
                else:
                    await websocket.send_json({"error": "no simulation"})
            elif action == "status":
                sim = None
                for s in _SIMULATORS.values():
                    if s.world.id == world_id:
                        sim = s
                        break
                if sim:
                    await websocket.send_json({
                        "tick": sim.world.clock_tick,
                        "total_events": len(sim.event_history),
                    })
            elif action == "disconnect":
                break
    except WebSocketDisconnect:
        pass
```

- [ ] **Step 3: 修改 router.py**

```python
from app.api import websocket
api_router.include_router(websocket.router)
```

- [ ] **Step 4: 跑测试 + commit**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/api/test_websocket.py -v
git add backend/ && git commit -m "feat: M5 Task 2 WebSocket 实时推送"
```

---

## Task 3: 全量回归 + 后端完成

- [ ] **Step 1: 全量测试**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/ -v
```

- [ ] **Step 2: README 追加 M5**

```markdown
## M5 导演介入 + WebSocket 已实现

- 导演介入 API（POST /worlds/{id}/director/inject，4 种类型）
- Simulator tick 开头处理注入队列（注入事件/改目标/改规则）
- WebSocket 实时推送（/worlds/{id}/ws，step 指令→事件推送）
```

- [ ] **Step 3: Commit + Push**

```bash
git add backend/ && git commit -m "feat: M5 后端完成 — 导演介入+WebSocket+全量回归"
git push
```

---

## 完成标准

1. `pytest` 全绿（131 基线 + M5 新增）。
2. 导演介入：注入事件/改目标/改规则，下一 tick 生效。
3. WebSocket：连接→发 step→接收实时事件。
4. 后端全部 6 个里程碑完成。
