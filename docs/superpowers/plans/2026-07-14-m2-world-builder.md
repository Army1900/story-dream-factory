# M2 世界构建助手 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现世界构建助手——和导演进行 7 阶段对话，从模板起步，逐步构建出结构化的 World 对象（含视觉锚定），定稿时做健康检查。

**Architecture:** `app/worldbuilder/` 模块，核心是 `BuilderSession` 状态机（7 阶段 + 后台清单 + 已收集数据）。对话通过 LLM 网关（M1 的 `LLMGateway`）驱动，视觉锚定通过生图网关（M1 的 `ImageGateway`）。BuilderSession 是内存状态（可序列化到 DB），不阻塞模拟循环。

**Tech Stack:** Python 3.13、FastAPI、SQLModel、httpx（LLM/生图）、pytest。

---

## 关键约定

1. **代码位于 `backend/`**，命令在 `backend/` 下运行。
2. **测试用 `.venv/Scripts/python.exe -m pytest`**（不用 uv run，避免 litellm 触发）。
3. **LLM/生图 mock 测试**（不真实调用 API）。mock `LLMGateway.complete` / `ImageGateway.generate`。
4. **BuilderSession 内存状态**：对话进行中存在内存（dict），定稿时写入 DB（World + Character + Relationship）。
5. **7 阶段**：`vision` → `setting` → `rules` → `locations` → `characters` → `inciting` → `finalize`。
6. **每任务结尾 commit**，结尾附 `Co-Authored-By: Claude <noreply@anthropic.com>`。

## 目标文件结构

```
backend/
  app/
    worldbuilder/
      __init__.py
      stages.py          # 7 阶段定义 + 每阶段清单维度
      session.py         # BuilderSession 状态机
      conversation.py    # ConversationService（LLM 对话核心）
      consistency.py     # 矛盾检测
      health_check.py    # 定稿健康检查
      templates.py       # 3 个预设 WorldTemplate 种子数据
      visual_anchor.py   # 视觉锚定（风格锚 + 角色定义图）
    api/
      builder.py         # 世界构建 API 端点
  tests/
    worldbuilder/
      __init__.py
      test_stages.py
      test_session.py
      test_conversation.py
      test_consistency.py
      test_health_check.py
      test_templates.py
      test_visual_anchor.py
```

---

## Task 1: 阶段定义 + 预设模板

**Files:**
- Create: `app/worldbuilder/__init__.py`（空）
- Create: `app/worldbuilder/stages.py`
- Create: `app/worldbuilder/templates.py`
- Test: `tests/worldbuilder/__init__.py`（空）
- Test: `tests/worldbuilder/test_stages.py`
- Test: `tests/worldbuilder/test_templates.py`

- [ ] **Step 1: 写测试 `tests/worldbuilder/test_stages.py`**

```python
from app.worldbuilder.stages import STAGES, STAGE_ORDER

def test_stages_are_seven():
    assert len(STAGE_ORDER) == 7

def test_stage_order():
    assert STAGE_ORDER == ["vision","setting","rules","locations","characters","inciting","finalize"]

def test_each_stage_has_checklist():
    for key in STAGE_ORDER:
        s = STAGES[key]
        assert s["title"]
        assert isinstance(s["checklist"], list) and len(s["checklist"]) > 0
        assert s["prompt_hint"]

def test_vision_stage_has_visual_style():
    assert "视觉风格" in STAGES["vision"]["checklist"]
```

- [ ] **Step 2: 写测试 `tests/worldbuilder/test_templates.py`**

```python
from app.worldbuilder.templates import BUILTIN_TEMPLATES

def test_three_templates():
    assert len(BUILTIN_TEMPLATES) == 3

def test_template_has_genre_and_drafts():
    for t in BUILTIN_TEMPLATES:
        assert t["name"]
        assert t["genre"]
        assert isinstance(t["rules_draft"], list)
        assert isinstance(t["visual_style_draft"], dict)

def test_template_genres_differ():
    genres = [t["genre"] for t in BUILTIN_TEMPLATES]
    assert len(set(genres)) == 3
```

- [ ] **Step 3: 实现 `app/worldbuilder/stages.py`**

```python
STAGE_ORDER = ["vision","setting","rules","locations","characters","inciting","finalize"]

STAGES = {
    "vision":     {"title":"愿景","checklist":["类型与基调","规模","视觉风格"],"prompt_hint":"你想讲一个什么样的故事？"},
    "setting":    {"title":"世界观","checklist":["时代","世界设定","核心矛盾"],"prompt_hint":"这个世界从何而来？核心矛盾是什么？"},
    "rules":      {"title":"规则","checklist":["世界法则(至少3条)","力量体系边界"],"prompt_hint":"这个世界遵循什么规则？"},
    "locations":  {"title":"地点","checklist":["关键地点(至少3个)","连通关系"],"prompt_hint":"故事发生在哪里？"},
    "characters": {"title":"角色","checklist":["角色(至少2个)","性格/目标","角色间张力","角色定义图"],"prompt_hint":"谁来登场？"},
    "inciting":   {"title":"开场","checklist":["初始态势","引爆事件"],"prompt_hint":"从哪个瞬间开始？"},
    "finalize":   {"title":"定稿","checklist":["健康检查","视觉锚确认","开拍"],"prompt_hint":"准备好开拍了吗？"},
}

def next_stage(current: str) -> str | None:
    idx = STAGE_ORDER.index(current)
    return STAGE_ORDER[idx+1] if idx < len(STAGE_ORDER)-1 else None

def prev_stage(current: str) -> str | None:
    idx = STAGE_ORDER.index(current)
    return STAGE_ORDER[idx-1] if idx > 0 else None
```

- [ ] **Step 4: 实现 `app/worldbuilder/templates.py`**

```python
BUILTIN_TEMPLATES = [
    {"name":"中世纪奇幻","genre":"fantasy","description":"魔法衰落中的王国","vision_draft":"黑暗奇幻史诗","setting_draft":"魔法衰退、旧秩序崩塌","rules_draft":["魔法稀有，施法付代价","誓言有约束力","暴力会被通缉"],"locations_draft":["边境贸易镇","王城","北境荒原"],"characters_draft":[],"visual_style_draft":{"art_style":"电影感写实","palette":"冷峻墨蓝","medium":"数字油画"}},
    {"name":"赛博朋克","genre":"cyberpunk","description":"2087企业垄断的未来","vision_draft":"反乌托邦赛博","setting_draft":"企业战争后的废墟","rules_draft":["信用归零=社会性死亡","记忆删除不可逆","AI不得越权"],"locations_draft":["下城区贫民窟","企业天空塔","数据深渊"],"characters_draft":[],"visual_style_draft":{"art_style":"赛博朋克","palette":"霓虹紫粉","medium":"数字插画"}},
    {"name":"东方仙侠","genre":"xianxia","description":"仙门林立的修仙界","vision_draft":"修仙玄幻","setting_draft":"灵气衰退、天劫将至","rules_draft":["天道不可逆","渡劫期不可干扰","因果业力"],"locations_draft":["九霄山祖庭","碧落海","幽冥渊"],"characters_draft":[],"visual_style_draft":{"art_style":"水墨飘逸","palette":"玄青紫金","medium":"数字水墨"}},
]
```

- [ ] **Step 5: 跑测试 + commit**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/worldbuilder/test_stages.py tests/worldbuilder/test_templates.py -v
git add backend/ && git commit -m "feat: M2 Task 1 阶段定义+预设模板"
```

---

## Task 2: BuilderSession 状态机

**Files:**
- Create: `app/worldbuilder/session.py`
- Test: `tests/worldbuilder/test_session.py`

- [ ] **Step 1: 写测试 `tests/worldbuilder/test_session.py`**

```python
import pytest
from app.worldbuilder.session import BuilderSession

def test_session_starts_at_vision():
    s = BuilderSession(template=None)
    assert s.current_stage == "vision"
    assert s.stage_index == 0

def test_advance_stage():
    s = BuilderSession(template=None)
    s.advance()
    assert s.current_stage == "setting"

def test_advance_past_final_returns_none():
    s = BuilderSession(template=None)
    for _ in range(7):
        s.advance()
    assert s.advance() is None  # 已到 finalize 之后

def test_go_back():
    s = BuilderSession(template=None)
    s.advance()  # setting
    s.advance()  # rules
    s.go_back()  # setting
    assert s.current_stage == "setting"

def test_go_back_from_first_stays():
    s = BuilderSession(template=None)
    s.go_back()
    assert s.current_stage == "vision"

def test_collect_data():
    s = BuilderSession(template=None)
    s.collect("vision", {"type":"奇幻","tone":"黑暗"})
    assert s.collected["vision"]["type"] == "奇幻"

def test_template_pre_fills():
    tpl = {"name":"t","genre":"fantasy","rules_draft":["r1"],"visual_style_draft":{"art":"oil"}}
    s = BuilderSession(template=tpl)
    assert s.collected["rules"] == ["r1"]
    assert s.collected["visual_style"]["art"] == "oil"

def test_checklist_progress():
    s = BuilderSession(template=None)
    s.collect("vision", {"type":"奇幻","tone":"黑暗","visual_style":{"art":"oil"}})
    progress = s.checklist_progress()
    assert progress["vision"]["covered"] >= 2  # type + visual_style

def test_serialize_deserialize():
    s = BuilderSession(template=None)
    s.collect("vision", {"type":"奇幻"})
    s.advance()
    data = s.to_dict()
    s2 = BuilderSession.from_dict(data)
    assert s2.current_stage == "setting"
    assert s2.collected["vision"]["type"] == "奇幻"
```

- [ ] **Step 2: 实现 `app/worldbuilder/session.py`**

```python
from __future__ import annotations
from app.worldbuilder.stages import STAGES, STAGE_ORDER, next_stage, prev_stage


class BuilderSession:
    """世界构建会话状态机：7 阶段 + 已收集数据 + 清单进度。"""

    def __init__(self, template: dict | None = None):
        self.current_stage: str = "vision"
        self.stage_index: int = 0
        self.collected: dict = {}
        self.messages: list[dict] = []
        self.world_name: str = ""
        if template:
            self._apply_template(template)

    def _apply_template(self, tpl: dict) -> None:
        if tpl.get("rules_draft"):
            self.collected["rules"] = list(tpl["rules_draft"])
        if tpl.get("visual_style_draft"):
            self.collected["visual_style"] = dict(tpl["visual_style_draft"])
        if tpl.get("locations_draft"):
            self.collected["locations"] = list(tpl["locations_draft"])
        self.world_name = tpl.get("name", "")

    def advance(self) -> str | None:
        nxt = next_stage(self.current_stage)
        if nxt is None:
            return None
        self.current_stage = nxt
        self.stage_index = STAGE_ORDER.index(nxt)
        return nxt

    def go_back(self) -> str:
        prv = prev_stage(self.current_stage)
        if prv:
            self.current_stage = prv
            self.stage_index = STAGE_ORDER.index(prv)
        return self.current_stage

    def go_to(self, stage: str) -> None:
        if stage in STAGE_ORDER:
            self.current_stage = stage
            self.stage_index = STAGE_ORDER.index(stage)

    def collect(self, stage: str, data: dict) -> None:
        if stage not in self.collected or not isinstance(self.collected[stage], dict):
            self.collected[stage] = {}
        if isinstance(data, dict):
            self.collected[stage].update(data)

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def checklist_progress(self) -> dict:
        result = {}
        for key in STAGE_ORDER:
            stage_def = STAGES[key]
            items = stage_def["checklist"]
            covered = 0
            stage_data = self.collected.get(key, {})
            # 简易覆盖检测：checklist 关键词在 collected 中有对应 key
            mapping = {
                "类型与基调": "type" in stage_data or "tone" in stage_data,
                "视觉风格": "visual_style" in self.collected or "visual_style" in stage_data,
                "核心矛盾": "conflict" in stage_data,
                "世界法则(至少3条)": isinstance(self.collected.get("rules"), list) and len(self.collected.get("rules", [])) >= 3,
                "关键地点(至少3个)": isinstance(self.collected.get("locations"), list) and len(self.collected.get("locations", [])) >= 3,
                "角色(至少2个)": isinstance(self.collected.get("characters"), list) and len(self.collected.get("characters", [])) >= 2,
                "引爆事件": "inciting_event" in self.collected or "inciting_event" in stage_data,
            }
            for item in items:
                if mapping.get(item, False):
                    covered += 1
            result[key] = {"covered": covered, "total": len(items)}
        return result

    def to_dict(self) -> dict:
        return {
            "current_stage": self.current_stage,
            "stage_index": self.stage_index,
            "collected": self.collected,
            "messages": self.messages,
            "world_name": self.world_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BuilderSession:
        s = cls(template=None)
        s.current_stage = data.get("current_stage", "vision")
        s.stage_index = data.get("stage_index", 0)
        s.collected = data.get("collected", {})
        s.messages = data.get("messages", [])
        s.world_name = data.get("world_name", "")
        return s
```

- [ ] **Step 3: 跑测试 + commit**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/worldbuilder/test_session.py -v
git add backend/ && git commit -m "feat: M2 Task 2 BuilderSession 状态机"
```

---

## Task 3: 对话核心（ConversationService）

**Files:**
- Create: `app/worldbuilder/conversation.py`
- Test: `tests/worldbuilder/test_conversation.py`

- [ ] **Step 1: 写测试 `tests/worldbuilder/test_conversation.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.worldbuilder.session import BuilderSession
from app.worldbuilder.conversation import ConversationService

def _mock_llm(reply="好的，收到。", extracted=None):
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=reply)
    llm.complete_json = AsyncMock(return_value=extracted or {})
    return llm

@pytest.mark.asyncio
async def test_conversation_returns_reply():
    llm = _mock_llm("你想讲什么样的故事？")
    svc = ConversationService(llm)
    session = BuilderSession(template=None)
    reply = await svc.process_message(session, "我想讲一个黑暗奇幻故事")
    assert "黑暗奇幻" in reply or len(reply) > 0
    assert llm.complete.await_count == 1

@pytest.mark.asyncio
async def test_conversation_extracts_structured_data():
    llm = _mock_llm("收到", {"type":"奇幻","tone":"黑暗","visual_style":{"art_style":"油画"}})
    svc = ConversationService(llm)
    session = BuilderSession(template=None)
    await svc.process_message(session, "黑暗奇幻")
    assert session.collected.get("vision", {}).get("type") == "奇幻"

@pytest.mark.asyncio
async def test_advance_when_user_says_next():
    llm = _mock_llm()
    svc = ConversationService(llm)
    session = BuilderSession(template=None)
    await svc.process_message(session, "完成，下一步")
    assert session.current_stage == "setting"

@pytest.mark.asyncio
async def test_go_back_when_user_says_back():
    llm = _mock_llm()
    svc = ConversationService(llm)
    session = BuilderSession(template=None)
    session.advance()  # setting
    await svc.process_message(session, "回到上一步")
    assert session.current_stage == "vision"

@pytest.mark.asyncio
async def test_message_recorded():
    llm = _mock_llm("回复")
    svc = ConversationService(llm)
    session = BuilderSession(template=None)
    await svc.process_message(session, "hello")
    assert len(session.messages) == 2  # user + assistant
    assert session.messages[0]["role"] == "user"
    assert session.messages[1]["role"] == "assistant"
```

- [ ] **Step 2: 实现 `app/worldbuilder/conversation.py`**

```python
from __future__ import annotations
import json
from app.worldbuilder.session import BuilderSession
from app.worldbuilder.stages import STAGES


class ConversationService:
    """处理导演消息 → LLM 回复 + 结构化数据提取 + 阶段推进。"""

    def __init__(self, llm_gateway):
        self.llm = llm_gateway

    async def process_message(self, session: BuilderSession, user_message: str) -> str:
        session.add_message("user", user_message)

        # 检查阶段控制指令
        lowered = user_message.lower().strip()
        if any(kw in lowered for kw in ["完成", "下一步", "next", "进入下一步"]):
            session.advance()
            stage = STAGES[session.current_stage]
            reply = f"进入「{stage['title']}」阶段。{stage['prompt_hint']}"
            session.add_message("assistant", reply)
            return reply
        if any(kw in lowered for kw in ["回到上一步", "返回", "back", "上一步"]):
            session.go_back()
            stage = STAGES[session.current_stage]
            reply = f"回到「{stage['title']}」阶段。{stage['prompt_hint']}"
            session.add_message("assistant", reply)
            return reply

        # 构建 LLM prompt
        stage = STAGES[session.current_stage]
        system_prompt = self._build_system_prompt(session)
        messages = [{"role": "system", "content": system_prompt}] + session.messages[-10:]

        # LLM 回复
        reply = await self.llm.complete(messages=messages)
        session.add_message("assistant", reply)

        # 结构化数据提取
        try:
            extracted = await self.llm.complete_json(
                messages=[{"role": "system", "content": f"从以下对话提取「{stage['title']}」阶段的结构化数据，输出 JSON。"},
                          {"role": "user", "content": f"用户说：{user_message}\n助手说：{reply}"}]
            )
            if extracted:
                session.collect(session.current_stage, extracted)
        except Exception:
            pass  # 提取失败不阻塞对话

        return reply

    def _build_system_prompt(self, session: BuilderSession) -> str:
        stage = STAGES[session.current_stage]
        return (
            f"你是「故事梦工厂」的世界构建助手。当前在「{stage['title']}」阶段。\n"
            f"本阶段需要覆盖：{', '.join(stage['checklist'])}\n"
            f"引导导演描述，补充追问未覆盖的维度。\n"
            f"已有的世界数据：{json.dumps(session.collected, ensure_ascii=False, default=str)}\n"
            f"回复简洁有引导性。当导演说「完成」时进入下一步。"
        )
```

- [ ] **Step 3: 跑测试 + commit**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/worldbuilder/test_conversation.py -v
git add backend/ && git commit -m "feat: M2 Task 3 对话核心 ConversationService"
```

---

## Task 4: 矛盾检测

**Files:**
- Create: `app/worldbuilder/consistency.py`
- Test: `tests/worldbuilder/test_consistency.py`

- [ ] **Step 1: 写测试 `tests/worldbuilder/test_consistency.py`**

```python
from app.worldbuilder.consistency import check_consistency, ConsistencyResult

def test_no_issues_on_empty():
    result = check_consistency({})
    assert result.ok
    assert len(result.issues) == 0

def test_rule_contradiction_detected():
    result = check_consistency({"rules": ["魔法可以复活死者", "魔法不可复活死者"]})
    assert not result.ok
    assert any("复活" in i for i in result.issues)

def test_too_few_rules_warns():
    result = check_consistency({"rules": ["只有一条规则"]})
    assert any("至少3条" in i for i in result.warnings)

def test_character_goal_conflict_detected():
    result = check_consistency({
        "characters": [
            {"name":"A","goal":"杀死B"},
            {"name":"B","goal":"杀死A"},
        ]
    })
    # 直接冲突目标是好的张力，不是矛盾——应该是 warning 不是 error
    assert result.ok  # 张力不是错误
    assert any("张力" in w or "冲突" in w for w in result.warnings)

def test_too_few_locations_warns():
    result = check_consistency({"locations": ["只有一个地点"]})
    assert any("至少3个" in i for i in result.warnings)

def test_visual_style_missing_warns():
    result = check_consistency({})
    assert any("视觉风格" in i for i in result.warnings)
```

- [ ] **Step 2: 实现 `app/worldbuilder/consistency.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ConsistencyResult:
    issues: list[str] = field(default_factory=list)      # 错误（必须修）
    warnings: list[str] = field(default_factory=list)     # 警告（建议修）

    @property
    def ok(self) -> bool:
        return len(self.issues) == 0


def check_consistency(collected: dict) -> ConsistencyResult:
    result = ConsistencyResult()

    rules = collected.get("rules", [])
    if isinstance(rules, list):
        # 检测矛盾规则（关键词相反）
        _check_rule_contradictions(rules, result)
        if len(rules) < 3:
            result.warnings.append(f"世界规则建议至少3条，当前{len(rules)}条")

    characters = collected.get("characters", [])
    if isinstance(characters, list):
        if len(characters) >= 2:
            result.warnings.append("检测到多个角色，确认角色间有足够张力")
        elif len(characters) < 2:
            result.warnings.append("角色建议至少2个")

    locations = collected.get("locations", [])
    if isinstance(locations, list) and len(locations) < 3:
        result.warnings.append(f"地点建议至少3个，当前{len(locations)}个")

    if not collected.get("visual_style"):
        result.warnings.append("视觉风格锚尚未确定")

    if not collected.get("vision"):
        result.warnings.append("愿景尚未确定")

    return result


_OPPOSITES = [
    ("可以", "不可"), ("能", "不能"), ("会", "不会"),
    ("必须", "禁止"), ("允许", "禁止"),
]

def _check_rule_contradictions(rules: list[str], result: ConsistencyResult) -> None:
    for i, r1 in enumerate(rules):
        for r2 in rules[i+1:]:
            for pos, neg in _OPPOSITES:
                if pos in r1 and neg in r2 and _share_keyword(r1, r2):
                    result.issues.append(f"规则可能矛盾：「{r1}」vs「{r2}」")
                elif neg in r1 and pos in r2 and _share_keyword(r1, r2):
                    result.issues.append(f"规则可能矛盾：「{r1}」vs「{r2}」")

def _share_keyword(r1: str, r2: str) -> bool:
    """两条规则是否有共同关键词（简单：共享 >=2 个汉字片段）。"""
    common = set(r1) & set(r2)
    return len(common) >= 3
```

- [ ] **Step 3: 跑测试 + commit**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/worldbuilder/test_consistency.py -v
git add backend/ && git commit -m "feat: M2 Task 4 矛盾检测"
```

---

## Task 5: 健康检查

**Files:**
- Create: `app/worldbuilder/health_check.py`
- Test: `tests/worldbuilder/test_health_check.py`

- [ ] **Step 1: 写测试 `tests/worldbuilder/test_health_check.py`**

```python
from app.worldbuilder.health_check import run_health_check, HealthReport

def test_healthy_world():
    collected = {
        "vision": {"type": "奇幻"},
        "rules": ["魔法稀有", "暴力通缉", "誓言约束"],
        "locations": ["镇", "城", "林"],
        "characters": [{"name": "A"}, {"name": "B"}],
        "visual_style": {"art_style": "油画"},
    }
    report = run_health_check(collected)
    assert report.passed
    assert len(report.errors) == 0

def test_missing_rules_fails():
    report = run_health_check({"rules": ["只有一条"]})
    assert not report.passed
    assert any("规则" in e for e in report.errors)

def test_missing_characters_fails():
    report = run_health_check({"rules": ["a","b","c"], "characters": []})
    assert not report.passed

def test_missing_visual_style_warns():
    report = run_health_check({
        "rules": ["a","b","c"], "locations": ["x","y","z"],
        "characters": [{"name":"A"},{"name":"B"}],
    })
    assert report.passed  # warning 不阻塞
    assert any("视觉" in w for w in report.warnings)

def test_report_has_checklist():
    report = run_health_check({})
    assert len(report.checklist) >= 5
    for item in report.checklist:
        assert "name" in item
        assert "status" in item  # "pass" | "warn" | "fail"
```

- [ ] **Step 2: 实现 `app/worldbuilder/health_check.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from app.worldbuilder.consistency import check_consistency


@dataclass
class HealthReport:
    checklist: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


def run_health_check(collected: dict) -> HealthReport:
    report = HealthReport()

    # 1. 规则
    rules = collected.get("rules", [])
    rules_ok = isinstance(rules, list) and len(rules) >= 3
    report.checklist.append({"name": "世界规则 ≥3 条", "status": "pass" if rules_ok else "fail"})
    if not rules_ok:
        report.errors.append(f"世界规则不足3条（当前{len(rules) if isinstance(rules,list) else 0}）")

    # 2. 角色
    chars = collected.get("characters", [])
    chars_ok = isinstance(chars, list) and len(chars) >= 2
    report.checklist.append({"name": "角色 ≥2 个", "status": "pass" if chars_ok else "fail"})
    if not chars_ok:
        report.errors.append("角色不足2个")

    # 3. 地点
    locs = collected.get("locations", [])
    locs_ok = isinstance(locs, list) and len(locs) >= 3
    report.checklist.append({"name": "地点 ≥3 个", "status": "pass" if locs_ok else "warn"})
    if not locs_ok:
        report.warnings.append("地点不足3个")

    # 4. 矛盾检测
    cons = check_consistency(collected)
    cons_ok = cons.ok
    report.checklist.append({"name": "无规则矛盾", "status": "pass" if cons_ok else "fail"})
    report.errors.extend(cons.issues)

    # 5. 视觉风格
    vs = collected.get("visual_style", {})
    vs_ok = bool(vs)
    report.checklist.append({"name": "视觉风格锚已定", "status": "pass" if vs_ok else "warn"})
    if not vs_ok:
        report.warnings.append("视觉风格锚未确定")

    # 6. 引爆事件
    inciting = collected.get("inciting") or collected.get("inciting_event")
    report.checklist.append({"name": "引爆事件已设", "status": "pass" if inciting else "warn"})
    if not inciting:
        report.warnings.append("引爆事件未设置")

    return report
```

- [ ] **Step 3: 跑测试 + commit**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/worldbuilder/test_health_check.py -v
git add backend/ && git commit -m "feat: M2 Task 5 健康检查"
```

---

## Task 6: 视觉锚定

**Files:**
- Create: `app/worldbuilder/visual_anchor.py`
- Test: `tests/worldbuilder/test_visual_anchor.py`

- [ ] **Step 1: 写测试 `tests/worldbuilder/test_visual_anchor.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.worldbuilder.visual_anchor import VisualAnchorService

def _mock_imagegen(return_bytes=b"fake-png"):
    ig = MagicMock()
    ig.generate = AsyncMock(return_value=return_bytes)
    return ig

@pytest.mark.asyncio
async def test_generate_style_reference():
    ig = _mock_imagegen()
    svc = VisualAnchorService(image_gateway=ig, image_store=MagicMock())
    visual_style = {"art_style": "油画", "palette": "冷蓝"}
    await svc.generate_style_reference("world-1", visual_style)
    assert ig.generate.await_count == 1
    # 确认 prompt 含风格锚
    call_kwargs = ig.generate.call_args.kwargs
    assert "油画" in call_kwargs["prompt"] or "油画" in ig.generate.call_args.args[0]

@pytest.mark.asyncio
async def test_generate_character_ref():
    ig = _mock_imagegen()
    store = MagicMock()
    store.save.return_value = "/data/images/w/c.png"
    svc = VisualAnchorService(image_gateway=ig, image_store=store)
    await svc.generate_character_ref("world-1", "c1", "艾伦，黑发疤脸的流亡骑士", {"art_style":"油画"})
    assert ig.generate.await_count == 1
    assert store.save.called

@pytest.mark.asyncio
async def test_style_prompt_includes_all_dims():
    ig = _mock_imagegen()
    svc = VisualAnchorService(image_gateway=ig, image_store=MagicMock())
    vs = {"art_style":"水彩","palette":"暖色","medium":"纸本","composition":"对称"}
    await svc.generate_style_reference("w1", vs)
    prompt = ig.generate.call_args.kwargs.get("prompt") or ig.generate.call_args.args[0]
    for v in vs.values():
        assert v in prompt
```

- [ ] **Step 2: 实现 `app/worldbuilder/visual_anchor.py`**

```python
from __future__ import annotations
from app.imagegen.gateway import build_prompt, ImageGateway
from app.persistence.image_store import ImageStore


class VisualAnchorService:
    """视觉锚定：风格参考图 + 角色定义图。"""

    def __init__(self, image_gateway: ImageGateway, image_store: ImageStore):
        self.imagegen = image_gateway
        self.store = image_store

    async def generate_style_reference(self, world_id: str, visual_style: dict, seed: int = 42) -> str:
        prompt = build_prompt(visual_style, "一个代表此世界整体视觉风格的概念图")
        data = await self.imagegen.generate(prompt=prompt, seed=seed)
        path = self.store.save(world_id=world_id, image_id="style-ref", data=data, ext="png")
        return path

    async def generate_character_ref(self, world_id: str, char_id: str, description: str, visual_style: dict, seed: int = 0) -> str:
        prompt = build_prompt(visual_style, f"角色立绘：{description}")
        data = await self.imagegen.generate(prompt=prompt, seed=seed)
        path = self.store.save(world_id=world_id, image_id=f"char-{char_id}", data=data, ext="png")
        return path
```

- [ ] **Step 3: 跑测试 + commit**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/worldbuilder/test_visual_anchor.py -v
git add backend/ && git commit -m "feat: M2 Task 6 视觉锚定"
```

---

## Task 7: 世界构建 API 端点

**Files:**
- Create: `app/api/builder.py`
- Modify: `app/api/router.py`
- Test: `tests/api/test_builder.py`

- [ ] **Step 1: 写测试 `tests/api/test_builder.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_session, set_engine
from app.worldbuilder.session import BuilderSession

def _setup_app(tmp_path):
    from sqlmodel import Session, SQLModel, create_engine
    engine = create_engine(f"sqlite:///{tmp_path/'t.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    set_engine(engine)
    def _gs():
        with Session(engine) as s:
            yield s
    app.dependency_overrides[get_session] = _gs
    return engine

def test_create_builder_session(client_fixture):
    resp = client_fixture.post("/worlds/builder/session", json={"template_index": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["stage"] == "vision"

def test_send_message(client_fixture, mock_llm):
    # 先创建 session
    resp = client_fixture.post("/worlds/builder/session", json={"template_index": 0})
    sid = resp.json()["session_id"]
    # 发消息
    resp = client_fixture.post(f"/worlds/builder/session/{sid}/message", json={"message": "黑暗奇幻"})
    assert resp.status_code == 200
    assert "reply" in resp.json()

def test_get_progress(client_fixture):
    resp = client_fixture.post("/worlds/builder/session", json={})
    sid = resp.json()["session_id"]
    resp = client_fixture.get(f"/worlds/builder/session/{sid}/progress")
    assert resp.status_code == 200
    assert "stage" in resp.json()
    assert "checklist" in resp.json()

def test_finalize(client_fixture, mock_llm):
    resp = client_fixture.post("/worlds/builder/session", json={"template_index": 0})
    sid = resp.json()["session_id"]
    resp = client_fixture.post(f"/worlds/builder/session/{sid}/finalize")
    assert resp.status_code == 200
    assert "world_id" in resp.json()
    assert "health" in resp.json()
```

> **注**：测试需要 `client_fixture` 和 `mock_llm` fixture。在 `conftest.py` 中添加（见 Step 3）。

- [ ] **Step 2: 实现 `app/api/builder.py`**

```python
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.api.deps import get_session
from app.worldbuilder.session import BuilderSession
from app.worldbuilder.templates import BUILTIN_TEMPLATES
from app.worldbuilder.stages import STAGES
from app.worldbuilder.conversation import ConversationService
from app.worldbuilder.health_check import run_health_check
from app.models.world import World
from app.models.character import Character
from app.models.location import Location
from app.persistence.repository import WorldRepository, CharacterRepository, LocationRepository

router = APIRouter(prefix="/worlds/builder", tags=["world-builder"])

# 内存中的 session 存储（MVP；后续可持久化到 DB）
_SESSIONS: dict[str, BuilderSession] = {}


def _get_llm():
    """获取 LLM 网关（MVP：延迟创建）。"""
    from app.config import get_settings
    from app.llm.config import TierConfig, LLMRoutingConfig
    from app.llm.gateway import LLMGateway
    settings = get_settings()
    routing = LLMRoutingConfig(
        tiers={"tier1": TierConfig(model=settings.llm_tier1_model)},
        default_tier="tier1",
    )
    return LLMGateway(routing=routing, api_key=settings.zhipu_api_key)


@router.post("/session")
def create_session(payload: dict):
    tpl_idx = payload.get("template_index")
    template = BUILTIN_TEMPLATES[tpl_idx] if tpl_idx is not None and tpl_idx < len(BUILTIN_TEMPLATES) else None
    session = BuilderSession(template=template)
    sid = str(uuid.uuid4())
    _SESSIONS[sid] = session
    stage = STAGES[session.current_stage]
    return {
        "session_id": sid,
        "stage": session.current_stage,
        "stage_title": stage["title"],
        "prompt_hint": stage["prompt_hint"],
        "checklist": stage["checklist"],
    }


@router.post("/session/{sid}/message")
async def send_message(sid: str, payload: dict):
    session = _SESSIONS.get(sid)
    if not session:
        return {"error": "session not found"}
    msg = payload.get("message", "")
    llm = _get_llm()
    svc = ConversationService(llm)
    reply = await svc.process_message(session, msg)
    stage = STAGES[session.current_stage]
    return {
        "reply": reply,
        "stage": session.current_stage,
        "stage_title": stage["title"],
        "checklist_progress": session.checklist_progress().get(session.current_stage, {}),
    }


@router.get("/session/{sid}/progress")
def get_progress(sid: str):
    session = _SESSIONS.get(sid)
    if not session:
        return {"error": "session not found"}
    return {
        "stage": session.current_stage,
        "collected": session.collected,
        "checklist": session.checklist_progress(),
        "messages": session.messages[-5:],
    }


@router.post("/session/{sid}/go-back")
def go_back(sid: str):
    session = _SESSIONS.get(sid)
    if not session:
        return {"error": "session not found"}
    session.go_back()
    stage = STAGES[session.current_stage]
    return {"stage": session.current_stage, "stage_title": stage["title"]}


@router.post("/session/{sid}/finalize")
def finalize_session(sid: str, session_db: Session = Depends(get_session)):
    session = _SESSIONS.get(sid)
    if not session:
        return {"error": "session not found"}

    # 健康检查
    health = run_health_check(session.collected)

    # 组装 World 对象
    collected = session.collected
    world = World(
        name=session.world_name or "新世界",
        vision=str(collected.get("vision", {}).get("type", "")),
        setting=str(collected.get("setting", "")),
        rules=collected.get("rules", []),
        visual_style=collected.get("visual_style", {}),
        initial_state=collected.get("inciting", {}),
    )
    repo = WorldRepository(session_db)
    repo.create(world)

    # 角色
    for ch in collected.get("characters", []):
        if isinstance(ch, dict):
            repo_ch = CharacterRepository(session_db)
            repo_ch.create(Character(
                world_id=world.id,
                name=ch.get("name", ""),
                archetype=ch.get("archetype", ""),
                goals=ch.get("goals", {}),
                personality=ch.get("personality", {}),
            ))

    # 地点
    for loc in collected.get("locations", []):
        if isinstance(loc, (str, dict)):
            name = loc if isinstance(loc, str) else loc.get("name", "")
            if name:
                repo_loc = LocationRepository(session_db)
                repo_loc.create(Location(world_id=world.id, name=name))

    return {
        "world_id": world.id,
        "health": {
            "passed": health.passed,
            "errors": health.errors,
            "warnings": health.warnings,
            "checklist": health.checklist,
        },
    }
```

- [ ] **Step 3: 在 `tests/conftest.py` 追加 builder 测试 fixtures**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture()
def mock_llm(monkeypatch):
    """Mock LLM 网关，避免真实 API 调用。"""
    mock = MagicMock()
    mock.complete = AsyncMock(return_value="这是助手的回复。")
    mock.complete_json = AsyncMock(return_value={})
    def _get_llm():
        return mock
    monkeypatch.setattr("app.api.builder._get_llm", _get_llm)
    return mock


@pytest.fixture()
def client_fixture(tmp_path):
    from sqlmodel import Session, SQLModel, create_engine
    from app.api.deps import get_session, set_engine

    engine = create_engine(f"sqlite:///{tmp_path/'builder.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    set_engine(engine)
    def _gs():
        with Session(engine) as s:
            yield s
    app.dependency_overrides[get_session] = _gs
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()
```

- [ ] **Step 4: 修改 `app/api/router.py` 加 builder 路由**

```python
from fastapi import APIRouter
from app.api import health, worlds
from app.api import builder

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(worlds.router)
api_router.include_router(builder.router)
```

- [ ] **Step 5: 跑测试 + commit**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/api/test_builder.py tests/worldbuilder/ -v
git add backend/ && git commit -m "feat: M2 Task 7 世界构建 API 端点"
```

---

## Task 8: 全量回归 + M2 完成

**Files:**
- Modify: `backend/README.md`

- [ ] **Step 1: 运行全部测试**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/ -v
```
Expected: 全部 PASS（M1 的 40 + M2 的新增）。

- [ ] **Step 2: 更新 README 追加 M2 状态**

在 `backend/README.md` 的 M1 段落后追加：

```markdown
## M2 世界构建助手已实现

- 7 阶段对话状态机（愿景→世界观→规则→地点→角色→开场→定稿）
- 3 个预设模板（奇幻/赛博/仙侠）
- 对话核心（LLM 回复 + 结构化数据提取 + 阶段推进/回退）
- 矛盾检测（规则矛盾/数量不足/张力检查）
- 健康检查（定稿体检）
- 视觉锚定（风格参考图 + 角色定义图）
- API：创建会话 / 发消息 / 进度 / 回退 / 定稿产出 World
```

- [ ] **Step 3: Commit**

```bash
git add backend/ && git commit -m "feat: M2 完成 — 全量回归 + README"
git push
```

---

## 完成标准

M2 完成后应满足：
1. `pytest` 全绿（M1 的 40 + M2 新增）。
2. `POST /worlds/builder/session` 创建会话（可选模板）。
3. `POST /worlds/builder/session/{id}/message` 对话（mock LLM 回复）。
4. `GET /worlds/builder/session/{id}/progress` 查看进度。
5. `POST /worlds/builder/session/{id}/finalize` 定稿 → 产出 World + 健康报告。
6. 视觉锚定通过 mock 生图网关生成参考图。
