# M3 单角色线 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用一个角色 + 最小世界意识（叙述者），跑通模拟引擎核心循环：角色感知→决策（ActionProposal）→世界意识叙述（Event）→写回。

**Architecture:** `app/agents/` 放角色 Agent 和世界意识 Agent；`app/engine/` 放模拟引擎。角色 Agent 用 LLM 生成结构化 ActionProposal，世界意识（叙述者）用 LLM 把提案转成文学叙述 Event。引擎编排单角色单 tick 循环。全部 mock 测试。

**Tech Stack:** Python 3.13、FastAPI、SQLModel、httpx（LLM）、pytest。

---

## 关键约定

1. **代码位于 `backend/`**，测试用 `.venv/Scripts/python.exe -m pytest`。
2. **LLM mock**：所有 LLM 调用 mock（`unittest.mock.AsyncMock`）。
3. **ActionProposal 是纯数据类**（dataclass），不是 SQLModel（过程数据，不持久化）。
4. **Event 是 SQLModel**（持久化到 DB，M1 已定义）。
5. **MVP 单角色**：不做物理引擎/导演注入/多角色并行。
6. **每任务 commit**。

## 目标文件结构

```
backend/
  app/
    agents/
      __init__.py
      proposal.py            # ActionProposal dataclass
      character_agent.py     # CharacterAgent（感知→决策→提案）
      narrator.py            # Narrator（提案→文学叙述 Event）
    engine/
      __init__.py
      simulator.py           # Simulator（单角色 tick 循环）
    api/
      simulation.py          # 模拟 API（start/step/status）
  tests/
    agents/
      __init__.py
      test_proposal.py
      test_character_agent.py
      test_narrator.py
    engine/
      __init__.py
      test_simulator.py
    api/
      test_simulation.py
```

---

## Task 1: ActionProposal 数据结构

**Files:**
- Create: `app/agents/__init__.py`（空）
- Create: `app/agents/proposal.py`
- Test: `tests/agents/__init__.py`（空）
- Test: `tests/agents/test_proposal.py`

- [ ] **Step 1: 写测试**

```python
# tests/agents/test_proposal.py
from app.agents.proposal import ActionProposal

def test_proposal_basic():
    p = ActionProposal(intent="质问贝拉", action_type="dialogue", target="贝拉", expectation="逼出真相", dialogue="你骗了我。")
    assert p.intent == "质问贝拉"
    assert p.action_type == "dialogue"
    assert p.target == "贝拉"

def test_proposal_optional_fields():
    p = ActionProposal(intent="等待", action_type="wait", target="", expectation="", dialogue="")
    assert p.action_type == "wait"

def test_proposal_to_dict():
    p = ActionProposal(intent="移动", action_type="move", target="酒馆", expectation="到达", dialogue="")
    d = p.to_dict()
    assert d["intent"] == "移动"
    assert d["action_type"] == "move"

def test_proposal_from_dict():
    d = {"intent":"攻击","action_type":"conflict","target":"敌人","expectation":"击败","dialogue":""}
    p = ActionProposal.from_dict(d)
    assert p.intent == "攻击"
    assert p.action_type == "conflict"

def test_proposal_from_llm_json():
    raw = '{"intent": "说服", "action_type": "dialogue", "target": "守卫", "expectation": "放行", "dialogue": "让我过去。"}'
    p = ActionProposal.from_llm_json(raw)
    assert p.target == "守卫"
```

- [ ] **Step 2: 实现 `app/agents/proposal.py`**

```python
from __future__ import annotations
import json
from dataclasses import dataclass, asdict


@dataclass
class ActionProposal:
    """角色 Agent 产出的行动提案（过程数据，不持久化）。"""
    intent: str = ""
    action_type: str = "action"  # action/dialogue/conflict/move/wait
    target: str = ""
    expectation: str = ""
    dialogue: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ActionProposal:
        return cls(
            intent=d.get("intent", ""),
            action_type=d.get("action_type", "action"),
            target=d.get("target", ""),
            expectation=d.get("expectation", ""),
            dialogue=d.get("dialogue", ""),
        )

    @classmethod
    def from_llm_json(cls, raw: str) -> ActionProposal:
        """从 LLM 返回的 JSON 字符串解析。"""
        return cls.from_dict(json.loads(raw))
```

- [ ] **Step 3: 跑测试 + commit**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/agents/test_proposal.py -v
git add backend/ && git commit -m "feat: M3 Task 1 ActionProposal 数据结构"
```

---

## Task 2: CharacterAgent（感知→决策→提案）

**Files:**
- Create: `app/agents/character_agent.py`
- Test: `tests/agents/test_character_agent.py`

- [ ] **Step 1: 写测试**

```python
# tests/agents/test_character_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.character_agent import CharacterAgent
from app.agents.proposal import ActionProposal
from app.models.character import Character

def _mock_llm(json_reply=None):
    llm = MagicMock()
    llm.complete = AsyncMock(return_value="回复")
    llm.complete_json = AsyncMock(return_value=json_reply or {
        "intent": "质问", "action_type": "dialogue",
        "target": "贝拉", "expectation": "真相", "dialogue": "你骗了我。"
    })
    return llm

def _make_character():
    return Character(
        id="c1", world_id="w1", name="艾伦",
        personality={"neuroticism": 0.8},
        backstory="流亡骑士",
        goals={"short_term": "复仇"},
        state={"location_id": "loc1", "health": 80, "mood": "愤怒"},
    )

def test_perceive_returns_context_string():
    llm = _mock_llm()
    agent = CharacterAgent(_make_character(), llm)
    snapshot = {"location": "酒馆", "present": ["艾伦", "贝拉"], "recent_events": ["T11 贝拉独坐"]}
    context = agent.perceive(snapshot)
    assert "酒馆" in context
    assert "贝拉" in context

@pytest.mark.asyncio
async def test_decide_returns_proposal():
    llm = _mock_llm()
    agent = CharacterAgent(_make_character(), llm)
    snapshot = {"location": "酒馆", "present": ["艾伦", "贝拉"], "recent_events": []}
    proposal = await agent.decide(snapshot)
    assert isinstance(proposal, ActionProposal)
    assert proposal.target == "贝拉"
    assert llm.complete_json.await_count == 1

@pytest.mark.asyncio
async def test_decide_prompt_includes_personality():
    llm = _mock_llm()
    agent = CharacterAgent(_make_character(), llm)
    snapshot = {"location": "酒馆", "present": ["贝拉"], "recent_events": []}
    await agent.decide(snapshot)
    # 验证 LLM 被调用（prompt 在 messages 里）
    call = llm.complete_json.call_args
    messages = call.kwargs.get("messages") or call.args[0]
    full_text = str(messages)
    assert "艾伦" in full_text  # 名字
    assert "复仇" in full_text or "流亡" in full_text  # 背景或目标

@pytest.mark.asyncio
async def test_decide_handles_llm_error():
    llm = MagicMock()
    llm.complete_json = AsyncMock(side_effect=Exception("LLM down"))
    agent = CharacterAgent(_make_character(), llm)
    snapshot = {"location": "酒馆", "present": [], "recent_events": []}
    proposal = await agent.decide(snapshot)
    # 降级：返回 wait 提案
    assert proposal.action_type == "wait"
```

- [ ] **Step 2: 实现 `app/agents/character_agent.py`**

```python
from __future__ import annotations
import json
from app.agents.proposal import ActionProposal
from app.models.character import Character


class CharacterAgent:
    """角色 Agent：感知世界 → 检索记忆 → 规划 → 产出 ActionProposal。"""

    def __init__(self, character: Character, llm_gateway, memories: list[dict] | None = None):
        self.character = character
        self.llm = llm_gateway
        self.memories = memories or []

    def perceive(self, world_snapshot: dict) -> str:
        """从世界快照提取角色能感知的，返回文本。"""
        parts = []
        loc = world_snapshot.get("location", "未知")
        parts.append(f"你在{loc}。")
        present = world_snapshot.get("present", [])
        if present:
            others = [p for p in present if p != self.character.name]
            if others:
                parts.append(f"在场：{'、'.join(others)}。")
        events = world_snapshot.get("recent_events", [])
        if events:
            parts.append(f"近期事件：{'; '.join(events[-3:])}")
        state = self.character.state or {}
        if state.get("mood"):
            parts.append(f"你的心情：{state['mood']}。")
        return " ".join(parts)

    def _build_decision_prompt(self, perception: str) -> list[dict]:
        c = self.character
        personality = c.personality or {}
        goals = c.goals or {}
        backstory = c.backstory or ""
        mem_text = "\n".join(f"- {m.get('content','')}" for m in self.memories[-5:]) if self.memories else "（无记忆）"

        system = (
            f"你是角色「{c.name}」的大脑。根据你的性格、目标和记忆，决定此刻做什么。\n"
            f"性格：{json.dumps(personality, ensure_ascii=False)}\n"
            f"背景：{backstory}\n"
            f"目标：{json.dumps(goals, ensure_ascii=False)}\n"
            f"记忆：\n{mem_text}\n\n"
            f"输出 JSON：{{\"intent\":\"意图\",\"action_type\":\"action|dialogue|conflict|move|wait\","
            f"\"target\":\"目标\",\"expectation\":\"预期\",\"dialogue\":\"对白或空\"}}"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": perception},
        ]

    async def decide(self, world_snapshot: dict) -> ActionProposal:
        """感知→规划→产出 ActionProposal。"""
        perception = self.perceive(world_snapshot)
        messages = self._build_decision_prompt(perception)
        try:
            data = await self.llm.complete_json(messages=messages)
            return ActionProposal.from_dict(data)
        except Exception:
            return ActionProposal(intent="等待", action_type="wait")
```

- [ ] **Step 3: 跑测试 + commit**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/agents/test_character_agent.py -v
git add backend/ && git commit -m "feat: M3 Task 2 CharacterAgent 感知→决策→提案"
```

---

## Task 3: Narrator（世界意识叙述者）

**Files:**
- Create: `app/agents/narrator.py`
- Test: `tests/agents/test_narrator.py`

- [ ] **Step 1: 写测试**

```python
# tests/agents/test_narrator.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.narrator import Narrator
from app.agents.proposal import ActionProposal
from app.models.event import Event

def _mock_llm(narration="木门被推开，寒风涌入。"):
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=narration)
    return llm

@pytest.mark.asyncio
async def test_narrate_returns_event():
    llm = _mock_llm()
    narrator = Narrator(llm)
    proposal = ActionProposal(intent="闯入", action_type="conflict", target="贝拉")
    event = await narrator.narrate(proposal, world_name="艾尔德兰", tick=12, location="酒馆")
    assert isinstance(event, Event)
    assert event.tick == 12
    assert event.narration  # 非空叙述
    assert llm.complete.await_count == 1

@pytest.mark.asyncio
async def test_narrate_uses_world_setting():
    llm = _mock_llm("叙述文本")
    narrator = Narrator(llm)
    proposal = ActionProposal(intent="说话", action_type="dialogue", target="贝拉", dialogue="你骗了我。")
    await narrator.narrate(proposal, world_name="艾尔德兰", tick=12, location="酒馆", world_setting="魔法衰落的王国")
    call = llm.complete.call_args
    messages = call.kwargs.get("messages") or call.args[0]
    full = str(messages)
    assert "艾尔德兰" in full or "魔法" in full

@pytest.mark.asyncio
async def test_narrate_fallback_on_error():
    llm = MagicMock()
    llm.complete = AsyncMock(side_effect=Exception("LLM down"))
    narrator = Narrator(llm)
    proposal = ActionProposal(intent="等待", action_type="wait")
    event = await narrator.narrate(proposal, world_name="w", tick=1, location="loc")
    assert event.narration  # 降级叙述（非空）
    assert "等待" in event.narration or "静" in event.narration  # 降级模板含关键词
```

- [ ] **Step 2: 实现 `app/agents/narrator.py`**

```python
from __future__ import annotations
from app.agents.proposal import ActionProposal
from app.models.event import Event
from app.models.enums import EventType


class Narrator:
    """世界意识-叙述者：把 ActionProposal 转成文学叙述 Event。"""

    def __init__(self, llm_gateway):
        self.llm = llm_gateway

    async def narrate(
        self,
        proposal: ActionProposal,
        world_name: str = "",
        tick: int = 0,
        location: str = "",
        world_setting: str = "",
    ) -> Event:
        messages = self._build_prompt(proposal, world_name, location, world_setting)
        try:
            narration = await self.llm.complete(messages=messages)
        except Exception:
            narration = self._fallback(proposal)

        event_type = self._map_type(proposal.action_type)
        return Event(
            tick=tick,
            type=event_type,
            participants=[proposal.target] if proposal.target else [],
            location_id=location,
            payload=proposal.to_dict(),
            narration=narration,
        )

    def _build_prompt(self, proposal: ActionProposal, world: str, loc: str, setting: str) -> list[dict]:
        system = (
            f"你是世界「{world}」的意识，一位文学叙述者。\n"
            f"世界观：{setting}\n"
            f"用 2-3 句优美的文学语言，叙述此刻发生的事。\n"
            f"不要角色第一人称，用第三人称全知视角。"
        )
        detail = (
            f"地点：{loc}\n"
            f"角色意图：{proposal.intent}\n"
            f"行动类型：{proposal.action_type}\n"
            f"目标：{proposal.target}\n"
        )
        if proposal.dialogue:
            detail += f"对白：「{proposal.dialogue}」\n"
        return [{"role": "system", "content": system}, {"role": "user", "content": detail}]

    def _map_type(self, action_type: str) -> EventType:
        mapping = {
            "dialogue": EventType.dialogue,
            "conflict": EventType.conflict,
            "move": EventType.action,
            "wait": EventType.action,
            "action": EventType.action,
        }
        return mapping.get(action_type, EventType.action)

    def _fallback(self, proposal: ActionProposal) -> str:
        """LLM 失败时的降级叙述。"""
        if proposal.dialogue:
            return f"角色说出了心中的话：「{proposal.dialogue}」"
        if proposal.action_type == "wait":
            return "一切陷入静默，时间仿佛凝滞。"
        return f"{proposal.intent}——在这一刻发生了。"
```

- [ ] **Step 3: 跑测试 + commit**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/agents/test_narrator.py -v
git add backend/ && git commit -m "feat: M3 Task 3 Narrator 叙述者"
```

---

## Task 4: Simulator（单角色 tick 循环）

**Files:**
- Create: `app/engine/__init__.py`（空）
- Create: `app/engine/simulator.py`
- Test: `tests/engine/__init__.py`（空）
- Test: `tests/engine/test_simulator.py`

- [ ] **Step 1: 写测试**

```python
# tests/engine/test_simulator.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.engine.simulator import Simulator
from app.models.world import World
from app.models.character import Character
from app.agents.proposal import ActionProposal
from app.models.event import Event

def _mock_llm():
    llm = MagicMock()
    llm.complete = AsyncMock(return_value="寒风卷着雪花涌入酒馆。")
    llm.complete_json = AsyncMock(return_value={
        "intent": "质问", "action_type": "dialogue",
        "target": "贝拉", "expectation": "真相", "dialogue": "你骗了我。"
    })
    return llm

def _make_world():
    return World(id="w1", name="艾尔德兰", setting="魔法衰落的王国", clock_tick=0)

def _make_character():
    return Character(id="c1", world_id="w1", name="艾伦",
                     personality={"neuroticism": 0.8}, backstory="流亡骑士",
                     goals={"short_term": "复仇"}, state={"location_id": "酒馆", "mood": "愤怒"})

@pytest.mark.asyncio
async def test_tick_returns_event():
    llm = _mock_llm()
    sim = Simulator(_make_world(), [_make_character()], llm)
    events = await sim.tick()
    assert len(events) >= 1
    assert isinstance(events[0], Event)
    assert events[0].narration  # 非空叙述

@pytest.mark.asyncio
async def test_tick_advances_clock():
    llm = _mock_llm()
    world = _make_world()
    sim = Simulator(world, [_make_character()], llm)
    assert world.clock_tick == 0
    await sim.tick()
    assert world.clock_tick == 1

@pytest.mark.asyncio
async def test_tick_event_has_correct_tick():
    llm = _mock_llm()
    world = _make_world()
    sim = Simulator(world, [_make_character()], llm)
    events = await sim.tick()
    assert events[0].tick == 0  # 事件记录的是推进前的 tick

@pytest.mark.asyncio
async def test_multiple_ticks():
    llm = _mock_llm()
    world = _make_world()
    sim = Simulator(world, [_make_character()], llm)
    await sim.tick()
    await sim.tick()
    await sim.tick()
    assert world.clock_tick == 3
    assert len(sim.event_history) == 3

@pytest.mark.asyncio
async def test_world_snapshot_built():
    llm = _mock_llm()
    sim = Simulator(_make_world(), [_make_character()], llm)
    snapshot = sim._build_snapshot()
    assert snapshot["location"]  # 有地点
    assert "艾伦" in snapshot["present"]
```

- [ ] **Step 2: 实现 `app/engine/simulator.py`**

```python
from __future__ import annotations
from app.agents.character_agent import CharacterAgent
from app.agents.narrator import Narrator
from app.models.world import World
from app.models.character import Character
from app.models.event import Event


class Simulator:
    """模拟引擎（M3 单角色版）：角色决策→叙述者叙述→写回。"""

    def __init__(self, world: World, characters: list[Character], llm_gateway):
        self.world = world
        self.characters = characters
        self.llm = llm_gateway
        self.narrator = Narrator(llm_gateway)
        self.agents = [CharacterAgent(c, llm_gateway) for c in characters]
        self.event_history: list[Event] = []

    def _build_snapshot(self) -> dict:
        """构建角色可感知的世界快照。"""
        locs = set()
        present = []
        for c in self.characters:
            state = c.state or {}
            loc = state.get("location_id", "未知")
            locs.add(loc)
            present.append(c.name)
        location = locs.pop() if locs else "未知"
        recent = [e.narration for e in self.event_history[-3:]] if self.event_history else []
        return {
            "location": location,
            "present": present,
            "recent_events": recent,
        }

    async def tick(self) -> list[Event]:
        """推进一个 tick：角色决策→叙述→写回。"""
        current_tick = self.world.clock_tick
        snapshot = self._build_snapshot()
        events: list[Event] = []

        for agent in self.agents:
            proposal = await agent.decide(snapshot)
            event = await self.narrator.narrate(
                proposal=proposal,
                world_name=self.world.name,
                tick=current_tick,
                location=snapshot["location"],
                world_setting=self.world.setting,
            )
            events.append(event)
            self.event_history.append(event)

        self.world.clock_tick += 1
        return events
```

- [ ] **Step 3: 跑测试 + commit**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/engine/test_simulator.py -v
git add backend/ && git commit -m "feat: M3 Task 4 Simulator 单角色 tick 循环"
```

---

## Task 5: 模拟 API（start/step/status）

**Files:**
- Create: `app/api/simulation.py`
- Modify: `app/api/router.py`
- Test: `tests/api/test_simulation.py`

- [ ] **Step 1: 写测试**

```python
# tests/api/test_simulation.py
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
```

- [ ] **Step 2: 实现 `app/api/simulation.py`**

```python
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.api.deps import get_session
from app.models.world import World
from app.models.character import Character
from app.engine.simulator import Simulator

router = APIRouter(prefix="/worlds/{world_id}/simulate", tags=["simulation"])

_SIMULATORS: dict[str, Simulator] = {}


def _get_llm():
    from app.config import get_settings
    from app.llm.config import TierConfig, LLMRoutingConfig
    from app.llm.gateway import LLMGateway
    settings = get_settings()
    routing = LLMRoutingConfig(
        tiers={"tier1": TierConfig(model=settings.llm_tier1_model)},
        default_tier="tier1",
    )
    return LLMGateway(routing=routing, api_key=settings.zhipu_api_key)


@router.post("/start")
def start_simulation(world_id: str, session_db: Session = Depends(get_session)):
    world = session_db.get(World, world_id)
    if not world:
        return {"error": "world not found"}
    chars = list(session_db.exec(select(Character).where(Character.world_id == world_id)).all())
    llm = _get_llm()
    sim = Simulator(world, chars, llm)
    sim_id = str(uuid.uuid4())
    _SIMULATORS[sim_id] = sim
    return {"sim_id": sim_id, "world": world.name, "characters": [c.name for c in chars], "tick": world.clock_tick}


@router.post("/step")
async def step_simulation(world_id: str):
    # 找到该世界的 simulator
    sim = None
    for sid, s in _SIMULATORS.items():
        if s.world.id == world_id:
            sim = s
            break
    if not sim:
        return {"error": "no active simulation for this world"}
    events = await sim.tick()
    return {
        "tick": sim.world.clock_tick,
        "events": [
            {"tick": e.tick, "type": e.type.value if hasattr(e.type, 'value') else str(e.type),
             "narration": e.narration, "participants": e.participants}
            for e in events
        ],
    }


@router.get("/status")
def simulation_status(world_id: str):
    sim = None
    for sid, s in _SIMULATORS.items():
        if s.world.id == world_id:
            sim = s
            break
    if not sim:
        return {"error": "no active simulation"}
    return {
        "tick": sim.world.clock_tick,
        "total_events": len(sim.event_history),
        "recent_narrations": [e.narration for e in sim.event_history[-5:]],
    }
```

- [ ] **Step 3: 修改 `app/api/router.py`**

```python
from fastapi import APIRouter
from app.api import health, worlds
from app.api import builder
from app.api import simulation

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(worlds.router)
api_router.include_router(builder.router)
api_router.include_router(simulation.router)
```

- [ ] **Step 4: 跑测试 + commit**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/api/test_simulation.py tests/agents/ tests/engine/ -v
git add backend/ && git commit -m "feat: M3 Task 5 模拟 API（start/step/status）"
```

---

## Task 6: 全量回归 + M3 完成

- [ ] **Step 1: 全量测试**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/ -v
```
Expected: 全部 PASS（M1 的 40 + M2 的 42 + M3 新增）。

- [ ] **Step 2: README 追加 M3**

在 `backend/README.md` 的 M2 段落后追加：

```markdown
## M3 单角色模拟已实现

- ActionProposal 行动提案（intent/action_type/target/expectation/dialogue）
- CharacterAgent（感知→决策→LLM 结构化提案，错误降级为 wait）
- Narrator 叙述者（提案→文学叙述 Event，错误降级模板）
- Simulator 模拟引擎（单角色 tick：决策→叙述→推进时钟→事件历史）
- API：`POST /worlds/{id}/simulate/start`、`POST /step`、`GET /status`
```

- [ ] **Step 3: Commit + Push**

```bash
git add backend/ && git commit -m "feat: M3 完成 — 全量回归 + README"
git push
```

---

## 完成标准

1. `pytest` 全绿（M1+M2 的 82 + M3 新增）。
2. `POST /worlds/{id}/simulate/start` 启动模拟。
3. `POST /worlds/{id}/simulate/step` 推进一个 tick，返回叙述事件。
4. `GET /worlds/{id}/simulate/status` 查看 tick + 事件数 + 近期叙述。
5. 单角色跑通"感知→决策→叙述"核心循环。
