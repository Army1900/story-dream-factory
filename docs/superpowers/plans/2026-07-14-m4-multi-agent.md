# M4 多角色线 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 M3 单角色基础上，实现多角色并行决策 + 物理引擎裁决 + 关系数值变化，让多个角色同时在世界里互动。

**Architecture:** M3 的 Simulator 扩展为多角色：阶段①角色并行决策（asyncio.gather）→ ②物理引擎确定性裁决（移动/资源/战斗/关系）→ ③世界意识叙述。新增 `app/physics/` 物理引擎模块。全部 mock 测试。

**Tech Stack:** Python 3.13、FastAPI、SQLModel、asyncio、pytest。

---

## 关键约定

1. **代码位于 `backend/`**，`.venv/Scripts/python.exe -m pytest`。
2. **LLM mock**（AsyncMock）。
3. **物理引擎不调 LLM**（纯确定性规则/数值）。
4. **每任务 commit**。

## 目标文件结构

```
backend/
  app/
    physics/
      __init__.py
      engine.py            # PhysicsEngine（裁决 ActionProposal → ResolvedAction）
      rules.py             # 数值规则（战斗/资源/关系变化）
    agents/
      proposal.py          # 已有，扩展 ResolvedAction
    engine/
      simulator.py         # 修改：多角色并行 + 物理引擎
  tests/
    physics/
      __init__.py
      test_engine.py
      test_rules.py
    engine/
      test_simulator.py    # 修改：多角色测试
```

---

## Task 1: ResolvedAction + 物理引擎核心

**Files:**
- Create: `app/physics/__init__.py`（空）
- Create: `app/physics/engine.py`
- Create: `app/physics/rules.py`
- Create: `tests/physics/__init__.py`（空）
- Test: `tests/physics/test_engine.py`
- Test: `tests/physics/test_rules.py`

- [ ] **Step 1: 写测试 `tests/physics/test_engine.py`**

```python
from app.physics.engine import PhysicsEngine, ResolvedAction
from app.agents.proposal import ActionProposal

def test_move_action_updates_location():
    engine = PhysicsEngine()
    proposal = ActionProposal(intent="去酒馆", action_type="move", target="酒馆")
    resolved = engine.resolve(proposal, character_state={"location_id": "营地"}, world_rules=[])
    assert resolved.success
    assert resolved.new_state["location_id"] == "酒馆"

def test_dialogue_passes_through():
    engine = PhysicsEngine()
    proposal = ActionProposal(intent="质问", action_type="dialogue", target="贝拉", dialogue="你骗了我。")
    resolved = engine.resolve(proposal, character_state={"location_id": "酒馆"}, world_rules=[])
    assert resolved.success
    assert resolved.new_state["location_id"] == "酒馆"  # 位置不变

def test_conflict_deals_damage():
    engine = PhysicsEngine()
    proposal = ActionProposal(intent="攻击", action_type="conflict", target="敌人")
    resolved = engine.resolve(proposal, character_state={"location_id": "战场", "health": 100}, world_rules=[])
    assert resolved.success
    assert resolved.new_state["health"] < 100  # 受伤

def test_wait_does_nothing():
    engine = PhysicsEngine()
    proposal = ActionProposal(intent="等待", action_type="wait")
    resolved = engine.resolve(proposal, character_state={"location_id": "酒馆", "health": 80}, world_rules=[])
    assert resolved.success
    assert resolved.new_state == {"location_id": "酒馆", "health": 80}

def test_rule_blocks_action():
    engine = PhysicsEngine()
    proposal = ActionProposal(intent="施法", action_type="action", target="复活死者")
    resolved = engine.resolve(proposal, character_state={}, world_rules=["魔法不可复活死者"])
    assert not resolved.success
    assert "违反" in resolved.reason or "不可" in resolved.reason
```

- [ ] **Step 2: 写测试 `tests/physics/test_rules.py`**

```python
from app.physics.rules import compute_damage, update_relationship, RELATIONSHIP_CHANGE

def test_damage_reduces_health():
    new_health = compute_damage(100, severity="moderate")
    assert new_health < 100
    assert new_health >= 50

def test_light_damage():
    new_health = compute_damage(100, severity="light")
    assert new_health == 90

def test_severe_damage():
    new_health = compute_damage(100, severity="severe")
    assert new_health <= 50

def test_relationship_decrease_on_conflict():
    new_affinity = update_relationship(0.0, action_type="conflict")
    assert new_affinity < 0.0

def test_relationship_increase_on_cooperation():
    new_affinity = update_relationship(0.0, action_type="dialogue", positive=True)
    assert new_affinity > 0.0
```

- [ ] **Step 3: 实现 `app/physics/engine.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from app.agents.proposal import ActionProposal
from app.physics.rules import compute_damage


@dataclass
class ResolvedAction:
    """物理引擎裁决后的行动结果。"""
    proposal: ActionProposal
    success: bool = True
    reason: str = ""
    new_state: dict = field(default_factory=dict)
    effects: dict = field(default_factory=dict)  # 副作用（关系变化等）


class PhysicsEngine:
    """确定性物理引擎：裁决 ActionProposal，不调 LLM。"""

    def resolve(self, proposal: ActionProposal, character_state: dict, world_rules: list[str]) -> ResolvedAction:
        # 检查规则约束
        blocked = self._check_rules(proposal, world_rules)
        if blocked:
            return ResolvedAction(proposal=proposal, success=False, reason=blocked, new_state=dict(character_state))

        atype = proposal.action_type
        new_state = dict(character_state)

        if atype == "move":
            new_state["location_id"] = proposal.target
        elif atype == "conflict":
            dmg = compute_damage(new_state.get("health", 100))
            new_state["health"] = dmg
        elif atype == "dialogue":
            pass  # 对白不改变物理状态
        elif atype == "wait":
            pass
        # action（通用）：不改变物理状态

        return ResolvedAction(proposal=proposal, success=True, reason="ok", new_state=new_state)

    def _check_rules(self, proposal: ActionProposal, rules: list[str]) -> str:
        """检查行动是否违反世界规则。返回空串=通过，否则返回违反原因。"""
        intent_lower = (proposal.intent + proposal.target).lower()
        for rule in rules:
            rule_lower = rule.lower()
            # 简单关键词匹配：如果规则含"不可X"且行动含"X"
            if "不可" in rule or "禁止" in rule:
                # 提取被禁止的关键词
                for marker in ("不可", "禁止"):
                    if marker in rule:
                        idx = rule.index(marker) + len(marker)
                        keyword = rule[idx:].strip()
                        if keyword and keyword in intent_lower:
                            return f"违反世界规则：「{rule}」"
        return ""
```

- [ ] **Step 4: 实现 `app/physics/rules.py`**

```python
from __future__ import annotations

# 战斗伤害
DAMAGE_TABLE = {"light": 10, "moderate": 25, "severe": 50}

def compute_damage(current_health: int, severity: str = "moderate") -> int:
    """计算受伤后的生命值。"""
    dmg = DAMAGE_TABLE.get(severity, 25)
    return max(0, current_health - dmg)

# 关系变化
RELATIONSHIP_CHANGE = {
    "conflict": -15,       # 冲突降好感
    "dialogue": 5,         # 对话略升（默认）
    "cooperation": 20,     # 合作升好感
    "betrayal": -30,       # 背叛暴降
}

def update_relationship(current_affinity: float, action_type: str, positive: bool = False) -> float:
    """更新角色间关系数值。"""
    if action_type == "dialogue" and positive:
        delta = RELATIONSHIP_CHANGE["cooperation"]
    else:
        delta = RELATIONSHIP_CHANGE.get(action_type, 0)
    return max(-100.0, min(100.0, current_affinity + delta))
```

- [ ] **Step 5: 跑测试 + commit**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/physics/ -v
git add backend/ && git commit -m "feat: M4 Task 1 物理引擎+数值规则"
```

---

## Task 2: Simulator 多角色并行 + 物理裁决

**Files:**
- Modify: `app/engine/simulator.py`
- Modify: `tests/engine/test_simulator.py`（追加多角色测试）

- [ ] **Step 1: 追加测试到 `tests/engine/test_simulator.py`**

```python
import asyncio
from app.engine.simulator import Simulator
from app.models.world import World
from app.models.character import Character
from unittest.mock import AsyncMock, MagicMock

def _mock_llm_multi():
    llm = MagicMock()
    llm.complete = AsyncMock(return_value="多个角色在这一刻行动。")
    llm.complete_json = AsyncMock(return_value={"intent":"行动","action_type":"action","target":"","expectation":"","dialogue":""})
    return llm

def _make_world():
    return World(id="w-m", name="艾尔德兰", setting="魔法衰落", clock_tick=0, rules=["魔法不可复活死者"])

def _make_chars():
    return [
        Character(id="c1", world_id="w-m", name="艾伦", goals={"short_term":"复仇"}, state={"location_id":"酒馆","health":100}),
        Character(id="c2", world_id="w-m", name="贝拉", goals={"short_term":"守护秘密"}, state={"location_id":"酒馆","health":100}),
        Character(id="c3", world_id="w-m", name="凯尔", goals={"short_term":"操纵"}, state={"location_id":"谋士塔","health":100}),
    ]

@pytest.mark.asyncio
async def test_multi_character_tick():
    llm = _mock_llm_multi()
    sim = Simulator(_make_world(), _make_chars(), llm)
    events = await sim.tick()
    assert len(events) == 3  # 三个角色各一个事件

@pytest.mark.asyncio
async def test_multi_tick_advances_clock_once():
    llm = _mock_llm_multi()
    world = _make_world()
    sim = Simulator(world, _make_chars(), llm)
    await sim.tick()
    assert world.clock_tick == 1  # 多角色但只推进一次

@pytest.mark.asyncio
async def test_physics_applied():
    llm = MagicMock()
    llm.complete = AsyncMock(return_value="叙述")
    llm.complete_json = AsyncMock(return_value={"intent":"去王城","action_type":"move","target":"王城","expectation":"","dialogue":""})
    world = _make_world()
    sim = Simulator(world, [_make_chars()[0]], llm)  # 只有艾伦
    await sim.tick()
    # 艾伦应该移动到王城
    assert sim.characters[0].state["location_id"] == "王城"

@pytest.mark.asyncio
async def test_conflict_updates_health():
    llm = MagicMock()
    llm.complete = AsyncMock(return_value="战斗")
    llm.complete_json = AsyncMock(return_value={"intent":"攻击","action_type":"conflict","target":"贝拉","expectation":"","dialogue":""})
    world = _make_world()
    chars = _make_chars()[:2]  # 艾伦 + 贝拉
    sim = Simulator(world, chars, llm)
    await sim.tick()
    # 艾伦攻击→贝拉应受伤（health 下降）
    bella = [c for c in sim.characters if c.name == "贝拉"][0]
    assert bella.state["health"] < 100
```

- [ ] **Step 2: 修改 `app/engine/simulator.py`（多角色 + 物理引擎）**

```python
from __future__ import annotations
import asyncio
from app.agents.character_agent import CharacterAgent
from app.agents.narrator import Narrator
from app.agents.proposal import ActionProposal
from app.physics.engine import PhysicsEngine, ResolvedAction
from app.physics.rules import update_relationship
from app.models.world import World
from app.models.character import Character
from app.models.event import Event


class Simulator:
    """模拟引擎（M4 多角色版）：并行决策→物理裁决→叙述。"""

    def __init__(self, world: World, characters: list[Character], llm_gateway):
        self.world = world
        self.characters = characters
        self.llm = llm_gateway
        self.narrator = Narrator(llm_gateway)
        self.physics = PhysicsEngine()
        self.agents = [CharacterAgent(c, llm_gateway) for c in characters]
        self.event_history: list[Event] = []

    def _build_snapshot(self) -> dict:
        locs = {}
        for c in self.characters:
            state = c.state or {}
            loc = state.get("location_id", "未知")
            locs.setdefault(loc, []).append(c.name)
        location = list(locs.keys())[0] if locs else "未知"
        present = [c.name for c in self.characters]
        recent = [e.narration for e in self.event_history[-3:]] if self.event_history else []
        return {"location": location, "present": present, "recent_events": recent, "locations": locs}

    async def tick(self) -> list[Event]:
        current_tick = self.world.clock_tick
        snapshot = self._build_snapshot()

        # ① 角色并行决策
        proposals = await asyncio.gather(*[a.decide(snapshot) for a in self.agents])

        # ② 物理引擎裁决
        resolved_actions: list[ResolvedAction] = []
        for agent, proposal in zip(self.agents, proposals):
            resolved = self.physics.resolve(
                proposal=proposal,
                character_state=dict(agent.character.state or {}),
                world_rules=self.world.rules or [],
            )
            # 应用状态变更到角色
            agent.character.state = resolved.new_state
            resolved_actions.append(resolved)

        # ③ 关系变化（基于行动类型）
        self._update_relationships(resolved_actions)

        # ④ 世界意识叙述（批量）
        events: list[Event] = []
        for resolved in resolved_actions:
            event = await self.narrator.narrate(
                proposal=resolved.proposal,
                world_name=self.world.name,
                tick=current_tick,
                location=resolved.new_state.get("location_id", "未知"),
                world_setting=self.world.setting,
            )
            events.append(event)
            self.event_history.append(event)

        self.world.clock_tick += 1
        return events

    def _update_relationships(self, actions: list[ResolvedAction]) -> None:
        """根据行动类型更新角色间关系（简化版：同地点的角色互相影响）。"""
        for i, act in enumerate(actions):
            if not act.success:
                continue
            atype = act.proposal.action_type
            if atype not in ("conflict", "dialogue", "cooperation"):
                continue
            target_name = act.proposal.target
            if not target_name:
                continue
            # 找目标角色
            for c in self.characters:
                if c.name == target_name:
                    current = (c.state or {}).get("affinity", {}).get(self.agents[i].character.name, 0.0)
                    new_val = update_relationship(current, atype)
                    c.state.setdefault("affinity", {})[self.agents[i].character.name] = new_val
                    break
```

- [ ] **Step 3: 跑测试 + commit**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/engine/ tests/physics/ -v
git add backend/ && git commit -m "feat: M4 Task 2 多角色并行+物理裁决"
```

---

## Task 3: 全量回归 + M4 完成

- [ ] **Step 1: 全量测试**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/ -v
```
Expected: 全部 PASS（102 基线 + M4 新增）。

- [ ] **Step 2: README 追加 M4**

在 `backend/README.md` M3 段落后追加：

```markdown
## M4 多角色模拟已实现

- 物理引擎（确定性裁决：移动/资源/战斗/关系，不调 LLM）
- 数值规则（伤害表 + 关系变化表）
- 规则约束检测（世界规则阻挡违规行动）
- 多角色并行决策（asyncio.gather）
- Simulator：并行决策→物理裁决→关系更新→批量叙述
- 同地点角色互相影响（冲突降好感、合作升好感）
```

- [ ] **Step 3: Commit + Push**

```bash
git add backend/ && git commit -m "feat: M4 完成 — 全量回归 + README"
git push
```

---

## 完成标准

1. `pytest` 全绿（102 基线 + M4 新增）。
2. 多角色 tick：3 个角色各产出 1 个事件。
3. 物理引擎：移动改位置、战斗扣血、规则阻挡违规。
4. 关系变化：冲突降好感、合作升好感。
5. 时钟每 tick 只推进一次（多角色共享时间）。
