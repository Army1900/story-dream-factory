# M1 地基（Foundation）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭好后端地基——可运行的 FastAPI 应用 + 完整领域模型 + SQLite 持久化 + 图像存储 + LLM 网关 + 生图网关，全部有测试覆盖，但**不含任何业务逻辑**（模拟引擎/Agent/世界构建的业务逻辑在 M2+）。

**Architecture:** 后端为单体 FastAPI 应用，位于 `backend/` 目录。领域模型用 **SQLModel**（同时是 Pydantic schema 和 SQLAlchemy 表模型，一份定义两用）。持久化用 SQLite + 仓储模式，`persistence/` 层隔离以便未来迁移。LLM 网关用 **LiteLLM** 封装多 provider + 分层路由 + fallback；生图网关用 httpx 直接对接国内 API + 抽象接口。配置走 pydantic-settings（环境变量）。

**Tech Stack:** Python 3.11+、uv（包管理）、FastAPI、SQLModel、SQLite、litellm、httpx、pytest + pytest-asyncio、pydantic-settings。

---

## 关键约定（所有任务遵守）

1. **代码位于 `backend/`**，命令在 `backend/` 目录下运行（用 `cd backend &&` 前缀）。
2. **包管理用 uv**：`uv add <pkg>`、`uv run pytest`、`uv run uvicorn app.main:app`。
3. **TDD 严格执行**：每个功能先写失败测试 → 运行验证失败 → 写最小实现 → 运行验证通过 → commit。
4. **ID 策略**：所有主键用 UUID 字符串，`Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)`。
5. **时间**：UTC，`datetime.now(timezone.utc)`。
6. **JSON 字段约定**：列表/字典/嵌套结构字段统一用 `sa_column=Column(JSON)` 存储；M1 不引入嵌套 Pydantic 子模型（YAGNI，M2+ 按需）。
7. **表名**：每个 SQLModel 表模型显式设 `__tablename__`（复数），FK 引用据此。
8. **字段重命名**：spec 里的 `World.model_config` 在 Pydantic 2 中是保留字（ConfigDict），实现时改名为 `World.llm_config`。
9. **每个任务结尾 commit**，commit message 用约定式格式（`feat:`/`test:`/`chore:` 等），结尾附 `Co-Authored-By: Claude <noreply@anthropic.com>`。
10. **M1 不真实调用外部 API**（LLM/生图），网关用 mock 测试；真实调用留一个手动脚本供开发者验证。

## 目标文件结构

```
backend/
├── pyproject.toml              # uv 项目 + 依赖
├── .env.example                # 配置模板
├── .gitignore
├── README.md                   # 启动说明
├── scripts/
│   ├── check_llm.py            # 手动验证 LLM 网关真实调用
│   └── check_imagegen.py       # 手动验证生图网关真实调用
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # pydantic-settings 配置
│   ├── models/
│   │   ├── __init__.py
│   │   ├── enums.py            # 共享枚举
│   │   ├── world.py            # World, WorldTemplate
│   │   ├── location.py         # Location
│   │   ├── character.py        # Character
│   │   ├── relationship.py     # Relationship
│   │   ├── event.py            # Event
│   │   ├── memory.py           # Memory
│   │   ├── image_asset.py      # ImageAsset
│   │   └── director.py         # DirectorDirective
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── db.py               # engine、get_session、init_db
│   │   ├── repository.py       # 仓储（BaseRepository + 各实体）
│   │   └── image_store.py      # 图像文件存储
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py           # 路由聚合
│   │   ├── health.py           # 健康检查
│   │   └── worlds.py           # World CRUD
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── config.py           # 分层路由配置
│   │   └── gateway.py          # LiteLLM 封装
│   └── imagegen/
│       ├── __init__.py
│       └── gateway.py          # 生图网关
└── tests/
    ├── __init__.py
    ├── conftest.py             # 测试 fixtures（内存 DB、临时图像目录）
    ├── test_health.py
    ├── test_config.py
    ├── models/
    │   ├── __init__.py
    │   ├── test_world.py
    │   ├── test_location.py
    │   ├── test_character.py
    │   ├── test_event.py
    │   └── test_misc_models.py
    ├── persistence/
    │   ├── __init__.py
    │   ├── test_db.py
    │   ├── test_repository.py
    │   └── test_image_store.py
    ├── api/
    │   ├── __init__.py
    │   └── test_worlds.py
    ├── llm/
    │   ├── __init__.py
    │   └── test_gateway.py
    └── imagegen/
        ├── __init__.py
        └── test_gateway.py
```

---

## Task 1: 项目脚手架与依赖

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.gitignore`
- Create: `backend/.env.example`
- Create: `backend/README.md`
- Create: `backend/app/__init__.py`（空）
- Create: `backend/app/main.py`
- Create: `backend/tests/__init__.py`（空）

- [ ] **Step 1: 创建 `backend/pyproject.toml`**

```toml
[project]
name = "story-dream-factory"
version = "0.1.0"
description = "多 Agent 故事世界模拟系统 - 后端"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlmodel>=0.0.22",
    "pydantic-settings>=2.5.0",
    "litellm>=1.50.0",
    "httpx>=0.27.0",
    "python-multipart>=0.0.9",
]

[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "anyio>=4.6.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["."]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]
```

- [ ] **Step 2: 创建 `backend/.gitignore`**

```
__pycache__/
*.py[cod]
.venv/
.env
data/
*.db
.pytest_cache/
.ruff_cache/
```

- [ ] **Step 3: 创建 `backend/.env.example`**

```
# 数据库（SQLite，相对 backend/ 目录）
DATABASE_URL=sqlite:///./data/story.db

# 图像存储目录
IMAGE_STORAGE_PATH=./data/images

# LLM 密钥（按需填一个即可）
ZHIPU_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# 默认模型分层（MVP 可全部用同一个）
LLM_TIER1_MODEL=openai/glm-4-plus
LLM_TIER2_MODEL=openai/glm-4-plus
LLM_TIER3_MODEL=openai/glm-4-flash
LLM_EMBEDDING_MODEL=

# 生图（智谱 CogView 示例）
IMAGEGEN_PROVIDER=zhipu
ZHIPU_IMAGE_MODEL=cogview-3
```

- [ ] **Step 4: 创建 `backend/app/main.py`（空应用骨架）**

```python
from fastapi import FastAPI

app = FastAPI(title="Story Dream Factory", version="0.1.0")
```

- [ ] **Step 5: 创建 `backend/README.md`**

````markdown
# Story Dream Factory — Backend

## 安装

需要 Python 3.11+ 和 [uv](https://docs.astral.sh/uv/)。

```bash
cd backend
uv sync
cp .env.example .env  # 按需填写密钥
```

## 运行测试

```bash
uv run pytest
```

## 启动开发服务器

```bash
uv run uvicorn app.main:app --reload
```
````

- [ ] **Step 6: 安装依赖并验证可导入**

Run:
```bash
cd backend && uv sync && uv run python -c "from app.main import app; print('ok')"
```
Expected: 打印 `ok`，无报错。

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "chore: 初始化后端项目脚手架与依赖

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: 健康检查端点（打通 FastAPI + 测试链路）

**Files:**
- Create: `backend/app/api/__init__.py`（空）
- Create: `backend/app/api/health.py`
- Create: `backend/app/api/router.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_health.py`
- Test: `backend/tests/conftest.py`

- [ ] **Step 1: 写失败测试 `backend/tests/test_health.py`**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && uv run pytest tests/test_health.py -v`
Expected: FAIL，报错 `AttributeError` 或 404（路由不存在）。

- [ ] **Step 3: 实现 `backend/app/api/health.py`**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 4: 实现 `backend/app/api/router.py`（聚合路由）**

```python
from fastapi import APIRouter

from app.api import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
```

- [ ] **Step 5: 修改 `backend/app/main.py` 挂载路由**

将 `backend/app/main.py` 替换为：

```python
from fastapi import FastAPI

from app.api.router import api_router

app = FastAPI(title="Story Dream Factory", version="0.1.0")
app.include_router(api_router)
```

- [ ] **Step 6: 运行测试验证通过**

Run: `cd backend && uv run pytest tests/test_health.py -v`
Expected: PASS。

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: 健康检查端点 /health

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: 配置模块（pydantic-settings）

**Files:**
- Create: `backend/app/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: 写失败测试 `backend/tests/test_config.py`**

```python
import os


def test_config_reads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./data/test.db")
    monkeypatch.setenv("IMAGE_STORAGE_PATH", "./data/images")
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
    monkeypatch.setenv("LLM_TIER1_MODEL", "openai/glm-4-plus")

    from app.config import Settings

    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///./data/test.db"
    assert settings.image_storage_path == "./data/images"
    assert settings.zhipu_api_key == "test-key"
    assert settings.llm_tier1_model == "openai/glm-4-plus"


def test_config_has_defaults(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from app.config import Settings

    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///./data/story.db"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && uv run pytest tests/test_config.py -v`
Expected: FAIL，`ModuleNotFoundError: app.config`。

- [ ] **Step 3: 实现 `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 存储
    database_url: str = "sqlite:///./data/story.db"
    image_storage_path: str = "./data/images"

    # LLM 密钥
    zhipu_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # LLM 分层模型
    llm_tier1_model: str = "openai/glm-4-plus"
    llm_tier2_model: str = "openai/glm-4-plus"
    llm_tier3_model: str = "openai/glm-4-flash"
    llm_embedding_model: str = ""

    # 生图
    imagegen_provider: str = "zhipu"
    zhipu_image_model: str = "cogview-3"


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && uv run pytest tests/test_config.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat: 配置模块（pydantic-settings）

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: 共享枚举 + World 与 WorldTemplate 模型

**Files:**
- Create: `backend/app/models/__init__.py`（空）
- Create: `backend/app/models/enums.py`
- Create: `backend/app/models/world.py`
- Test: `backend/tests/models/__init__.py`（空）
- Test: `backend/tests/models/test_world.py`

- [ ] **Step 1: 写失败测试 `backend/tests/models/test_world.py`**

```python
from app.models.world import World, WorldTemplate


def test_world_has_required_scalar_fields():
    world = World(name="艾尔德兰", vision="魔法衰落的王国")
    assert world.name == "艾尔德兰"
    assert world.vision == "魔法衰落的王国"
    assert world.clock_tick == 0
    assert world.rules == []
    assert world.state_flags == {}
    assert world.id  # 自动生成 UUID


def test_world_json_fields_accept_complex_values():
    world = World(
        name="t",
        vision="v",
        rules=["魔法稀有", "暴力会被通缉"],
        state_flags={"war_started": False},
        visual_style={"art_style": "oil-painting", "palette": "dark"},
        llm_config={"tier1": "openai/glm-4-plus"},
        initial_state={"opening_situation": "冬夜", "inciting_event": None},
    )
    assert world.rules == ["魔法稀有", "暴力会被通缉"]
    assert world.visual_style["art_style"] == "oil-painting"
    assert world.llm_config["tier1"] == "openai/glm-4-plus"


def test_world_template_defaults():
    tpl = WorldTemplate(name="中世纪奇幻", genre="fantasy")
    assert tpl.genre == "fantasy"
    assert tpl.rules_draft == []
    assert tpl.visual_style_draft == {}
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && uv run pytest tests/models/test_world.py -v`
Expected: FAIL，`ModuleNotFoundError`。

- [ ] **Step 3: 实现 `backend/app/models/enums.py`**

```python
from enum import Enum


class EventType(str, Enum):
    action = "action"
    dialogue = "dialogue"
    environment = "environment"
    conflict = "conflict"
    relationship_change = "relationship_change"
    director = "director"
    inciting = "inciting"


class MemoryType(str, Enum):
    observation = "observation"
    reflection = "reflection"
    plan = "plan"


class ImageAssetType(str, Enum):
    style_ref = "style_ref"
    character_ref = "character_ref"
    scene = "scene"


class DirectiveType(str, Enum):
    inject_event = "inject_event"
    set_goal = "set_goal"
    modify_world = "modify_world"
    force_action = "force_action"
```

- [ ] **Step 4: 实现 `backend/app/models/world.py`**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uid() -> str:
    return str(uuid.uuid4())


class World(SQLModel, table=True):
    __tablename__ = "worlds"

    id: str = Field(default_factory=_uid, primary_key=True)
    name: str
    vision: str = ""
    setting: str = ""
    rules: list = Field(default_factory=list, sa_column=Column(JSON))
    visual_style: dict = Field(default_factory=dict, sa_column=Column(JSON))
    clock_tick: int = 0
    clock_date: str = ""
    state_flags: dict = Field(default_factory=dict, sa_column=Column(JSON))
    initial_state: dict = Field(default_factory=dict, sa_column=Column(JSON))
    llm_config: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)

    # 注：spec 中该字段名为 model_config，因 Pydantic 2 保留字改名 llm_config


class WorldTemplate(SQLModel, table=True):
    __tablename__ = "world_templates"

    id: str = Field(default_factory=_uid, primary_key=True)
    name: str
    genre: str
    description: str = ""
    vision_draft: str = ""
    setting_draft: str = ""
    rules_draft: list = Field(default_factory=list, sa_column=Column(JSON))
    locations_draft: list = Field(default_factory=list, sa_column=Column(JSON))
    characters_draft: list = Field(default_factory=list, sa_column=Column(JSON))
    visual_style_draft: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd backend && uv run pytest tests/models/test_world.py -v`
Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: World 与 WorldTemplate 领域模型

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: Location 模型

**Files:**
- Create: `backend/app/models/location.py`
- Test: `backend/tests/models/test_location.py`

- [ ] **Step 1: 写失败测试 `backend/tests/models/test_location.py`**

```python
from app.models.location import Location


def test_location_defaults():
    loc = Location(name="酒馆", world_id="w1")
    assert loc.name == "酒馆"
    assert loc.world_id == "w1"
    assert loc.neighbors == []
    assert loc.occupants == []
    assert loc.resources == []
    assert loc.id


def test_location_with_connections():
    loc = Location(
        name="集市",
        world_id="w1",
        description="喧嚣的集市",
        neighbors=["loc-tavern", "loc-palace"],
        occupants=["char-a", "char-b"],
        resources=["金币", "面包"],
    )
    assert loc.neighbors == ["loc-tavern", "loc-palace"]
    assert len(loc.occupants) == 2
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && uv run pytest tests/models/test_location.py -v`
Expected: FAIL，`ModuleNotFoundError`。

- [ ] **Step 3: 实现 `backend/app/models/location.py`**

```python
from datetime import datetime

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.models.world import _now, _uid


class Location(SQLModel, table=True):
    __tablename__ = "locations"

    id: str = Field(default_factory=_uid, primary_key=True)
    world_id: str = Field(foreign_key="worlds.id", index=True)
    name: str
    description: str = ""
    neighbors: list = Field(default_factory=list, sa_column=Column(JSON))
    occupants: list = Field(default_factory=list, sa_column=Column(JSON))
    resources: list = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && uv run pytest tests/models/test_location.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat: Location 领域模型

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: Character 与 Relationship 模型

**Files:**
- Create: `backend/app/models/character.py`
- Create: `backend/app/models/relationship.py`
- Test: `backend/tests/models/test_character.py`

- [ ] **Step 1: 写失败测试 `backend/tests/models/test_character.py`**

```python
from app.models.character import Character
from app.models.relationship import Relationship


def test_character_defaults():
    c = Character(name="艾伦", world_id="w1")
    assert c.name == "艾伦"
    assert c.goals == {}
    assert c.state == {}
    assert c.personality == {}
    assert c.visual_definition == {}
    assert c.id


def test_character_with_complex_fields():
    c = Character(
        name="艾伦",
        world_id="w1",
        archetype="流亡者",
        personality={"openness": 0.3, "neuroticism": 0.8},
        backstory="曾是骑士",
        skills=["剑术", "生存"],
        goals={"short_term": "复仇", "long_term": " redemption"},
        state={"location_id": "loc-1", "health": 80, "mood": "愤怒"},
        visual_definition={"description": "黑发疤脸", "reference_image_url": None},
    )
    assert c.skills == ["剑术", "生存"]
    assert c.state["health"] == 80


def test_relationship_defaults():
    r = Relationship(
        world_id="w1", from_character_id="c1", to_character_id="c2"
    )
    assert r.affinity == 0.0
    assert r.trust == 0.0
    assert r.history == []
    assert r.id
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && uv run pytest tests/models/test_character.py -v`
Expected: FAIL，`ModuleNotFoundError`。

- [ ] **Step 3: 实现 `backend/app/models/character.py`**

```python
from datetime import datetime

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.models.world import _now, _uid


class Character(SQLModel, table=True):
    __tablename__ = "characters"

    id: str = Field(default_factory=_uid, primary_key=True)
    world_id: str = Field(foreign_key="worlds.id", index=True)
    name: str
    archetype: str = ""
    personality: dict = Field(default_factory=dict, sa_column=Column(JSON))
    backstory: str = ""
    skills: list = Field(default_factory=list, sa_column=Column(JSON))
    goals: dict = Field(default_factory=dict, sa_column=Column(JSON))
    state: dict = Field(default_factory=dict, sa_column=Column(JSON))
    visual_definition: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)
```

- [ ] **Step 4: 实现 `backend/app/models/relationship.py`**

```python
from datetime import datetime

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.models.world import _now, _uid


class Relationship(SQLModel, table=True):
    __tablename__ = "relationships"

    id: str = Field(default_factory=_uid, primary_key=True)
    world_id: str = Field(foreign_key="worlds.id", index=True)
    from_character_id: str = Field(foreign_key="characters.id", index=True)
    to_character_id: str = Field(foreign_key="characters.id", index=True)
    affinity: float = 0.0
    trust: float = 0.0
    history: list = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd backend && uv run pytest tests/models/test_character.py -v`
Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: Character 与 Relationship 领域模型

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 7: Event 模型

**Files:**
- Create: `backend/app/models/event.py`
- Test: `backend/tests/models/test_event.py`

- [ ] **Step 1: 写失败测试 `backend/tests/models/test_event.py`**

```python
from app.models.event import Event
from app.models.enums import EventType


def test_event_defaults():
    e = Event(world_id="w1", tick=0)
    assert e.world_id == "w1"
    assert e.tick == 0
    assert e.type == EventType.action
    assert e.participants == []
    assert e.payload == {}
    assert e.visibility == []
    assert e.narration == ""
    assert e.id


def test_event_with_payload():
    e = Event(
        world_id="w1",
        tick=3,
        type=EventType.dialogue,
        participants=["c1", "c2"],
        location_id="loc-1",
        payload={"text": "你骗了我！"},
        visibility=["c1", "c2"],
        narration="艾伦怒视着对方。",
    )
    assert e.type == EventType.dialogue
    assert e.payload["text"] == "你骗了我！"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && uv run pytest tests/models/test_event.py -v`
Expected: FAIL，`ModuleNotFoundError`。

- [ ] **Step 3: 实现 `backend/app/models/event.py`**

```python
from datetime import datetime

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.models.enums import EventType
from app.models.world import _now, _uid


class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: str = Field(default_factory=_uid, primary_key=True)
    world_id: str = Field(foreign_key="worlds.id", index=True)
    tick: int = Field(default=0, index=True)
    timestamp: datetime = Field(default_factory=_now)
    type: EventType = Field(default=EventType.action)
    participants: list = Field(default_factory=list, sa_column=Column(JSON))
    location_id: str = ""
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    narration: str = ""
    visibility: list = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && uv run pytest tests/models/test_event.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat: Event 领域模型

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 8: Memory、ImageAsset、DirectorDirective 模型

**Files:**
- Create: `backend/app/models/memory.py`
- Create: `backend/app/models/image_asset.py`
- Create: `backend/app/models/director.py`
- Test: `backend/tests/models/test_misc_models.py`

- [ ] **Step 1: 写失败测试 `backend/tests/models/test_misc_models.py`**

```python
from app.models.memory import Memory
from app.models.image_asset import ImageAsset
from app.models.director import DirectorDirective
from app.models.enums import MemoryType, ImageAssetType, DirectiveType


def test_memory_defaults():
    m = Memory(character_id="c1", world_id="w1")
    assert m.type == MemoryType.observation
    assert m.content == ""
    assert m.importance == 5.0
    assert m.embedding == []


def test_image_asset_defaults():
    a = ImageAsset(world_id="w1")
    assert a.type == ImageAssetType.style_ref
    assert a.prompt == ""
    assert a.seed == 0
    assert a.reference_image_ids == []
    assert a.url == ""


def test_directive_defaults():
    d = DirectorDirective(world_id="w1", effective_tick=5)
    assert d.type == DirectiveType.inject_event
    assert d.payload == {}
    assert d.target == ""
    assert d.effective_tick == 5
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && uv run pytest tests/models/test_misc_models.py -v`
Expected: FAIL，`ModuleNotFoundError`。

- [ ] **Step 3: 实现 `backend/app/models/memory.py`**

```python
from datetime import datetime

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.models.enums import MemoryType
from app.models.world import _now, _uid


class Memory(SQLModel, table=True):
    __tablename__ = "memories"

    id: str = Field(default_factory=_uid, primary_key=True)
    character_id: str = Field(foreign_key="characters.id", index=True)
    world_id: str = Field(foreign_key="worlds.id", index=True)
    type: MemoryType = Field(default=MemoryType.observation)
    content: str = ""
    timestamp: datetime = Field(default_factory=_now)
    tick: int = 0
    importance: float = 5.0
    embedding: list = Field(default_factory=list, sa_column=Column(JSON))
```

- [ ] **Step 4: 实现 `backend/app/models/image_asset.py`**

```python
from datetime import datetime

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.models.enums import ImageAssetType
from app.models.world import _now, _uid


class ImageAsset(SQLModel, table=True):
    __tablename__ = "image_assets"

    id: str = Field(default_factory=_uid, primary_key=True)
    world_id: str = Field(foreign_key="worlds.id", index=True)
    type: ImageAssetType = Field(default=ImageAssetType.style_ref)
    prompt: str = ""
    seed: int = 0
    reference_image_ids: list = Field(default_factory=list, sa_column=Column(JSON))
    url: str = ""
    related_event_id: str = ""
    created_at: datetime = Field(default_factory=_now)
```

- [ ] **Step 5: 实现 `backend/app/models/director.py`**

```python
from datetime import datetime

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.models.enums import DirectiveType
from app.models.world import _now, _uid


class DirectorDirective(SQLModel, table=True):
    __tablename__ = "director_directives"

    id: str = Field(default_factory=_uid, primary_key=True)
    world_id: str = Field(foreign_key="worlds.id", index=True)
    type: DirectiveType = Field(default=DirectiveType.inject_event)
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    target: str = ""
    effective_tick: int = 0
    created_at: datetime = Field(default_factory=_now)
```

- [ ] **Step 6: 运行测试验证通过**

Run: `cd backend && uv run pytest tests/models/test_misc_models.py -v`
Expected: PASS。

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: Memory、ImageAsset、DirectorDirective 模型

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 9: 数据库引擎、session 与 init_db

**Files:**
- Create: `backend/app/persistence/__init__.py`（空）
- Create: `backend/app/persistence/db.py`
- Test: `backend/tests/persistence/__init__.py`（空）
- Test: `backend/tests/persistence/test_db.py`
- Test: `backend/tests/conftest.py`

- [ ] **Step 1: 写测试 DB fixture `backend/tests/conftest.py`**

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import Session, SQLModel, create_engine

# 确保所有模型被注册到 SQLModel.metadata
import app.models.world  # noqa
import app.models.location  # noqa
import app.models.character  # noqa
import app.models.relationship  # noqa
import app.models.event  # noqa
import app.models.memory  # noqa
import app.models.image_asset  # noqa
import app.models.director  # noqa


@pytest.fixture()
def memory_db_url() -> str:
    return "sqlite:///:memory:"


@pytest.fixture()
def session(memory_db_url):
    engine = create_engine(memory_db_url, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()
```

- [ ] **Step 2: 写失败测试 `backend/tests/persistence/test_db.py`**

```python
from sqlmodel import Session, SQLModel, select

from app.models.world import World
from app.persistence.db import create_db_engine, init_db


def test_init_db_creates_all_tables(tmp_path):
    url = f"sqlite:///{tmp_path/'t.db'}"
    engine = create_db_engine(url)
    init_db(engine)
    with Session(engine) as s:
        # 能插入并查询即说明建表成功
        s.add(World(name="x"))
        s.commit()
        rows = s.exec(select(World)).all()
        assert len(rows) == 1
        assert rows[0].name == "x"
    engine.dispose()


def test_create_db_engine_returns_engine():
    engine = create_db_engine("sqlite:///:memory:")
    assert engine is not None
    engine.dispose()
```

- [ ] **Step 3: 运行测试验证失败**

Run: `cd backend && uv run pytest tests/persistence/test_db.py -v`
Expected: FAIL，`ModuleNotFoundError: app.persistence.db`。

- [ ] **Step 4: 实现 `backend/app/persistence/db.py`**

```python
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine


def create_db_engine(database_url: str, echo: bool = False) -> Engine:
    connect_args = (
        {"check_same_thread": False}
        if database_url.startswith("sqlite")
        else {}
    )
    return create_engine(database_url, echo=echo, connect_args=connect_args)


def init_db(engine: Engine) -> None:
    """创建所有表。需先 import 所有模型模块以注册到 metadata。"""
    import app.models.world  # noqa: F401
    import app.models.location  # noqa: F401
    import app.models.character  # noqa: F401
    import app.models.relationship  # noqa: F401
    import app.models.event  # noqa: F401
    import app.models.memory  # noqa: F401
    import app.models.image_asset  # noqa: F401
    import app.models.director  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session(engine: Engine):
    """FastAPI 依赖：返回 session 生成器。"""
    with Session(engine) as session:
        yield session
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd backend && uv run pytest tests/persistence/test_db.py -v`
Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: 数据库引擎、session 与建表

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 10: 仓储 —— BaseRepository 与 WorldRepository

**Files:**
- Create: `backend/app/persistence/repository.py`
- Test: `backend/tests/persistence/test_repository.py`

- [ ] **Step 1: 写失败测试 `backend/tests/persistence/test_repository.py`**

```python
from app.models.world import World
from app.persistence.repository import WorldRepository


def test_create_and_get_world(session):
    repo = WorldRepository(session)
    world = repo.create(World(name="艾尔德兰", vision="v"))
    fetched = repo.get(world.id)
    assert fetched is not None
    assert fetched.name == "艾尔德兰"


def test_list_worlds(session):
    repo = WorldRepository(session)
    repo.create(World(name="a"))
    repo.create(World(name="b"))
    rows = repo.list()
    assert len(rows) == 2


def test_delete_world(session):
    repo = WorldRepository(session)
    world = repo.create(World(name="a"))
    repo.delete(world.id)
    assert repo.get(world.id) is None


def test_update_world(session):
    repo = WorldRepository(session)
    world = repo.create(World(name="a"))
    world.name = "b"
    updated = repo.update(world)
    assert updated.name == "b"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && uv run pytest tests/persistence/test_repository.py -v`
Expected: FAIL，`ModuleNotFoundError`。

- [ ] **Step 3: 实现 `backend/app/persistence/repository.py`**

```python
from typing import Generic, Type, TypeVar

from sqlmodel import Session, SQLModel, select

from app.models.world import World

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """通用 CRUD 仓储。子类设 model。"""

    model: Type[T]

    def __init__(self, session: Session):
        self.session = session

    def get(self, id_: str) -> T | None:
        return self.session.get(self.model, id_)

    def list(self, limit: int = 100, offset: int = 0) -> list[T]:
        stmt = select(self.model).offset(offset).limit(limit)
        return list(self.session.exec(stmt).all())

    def create(self, obj: T) -> T:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def update(self, obj: T) -> T:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def delete(self, id_: str) -> None:
        obj = self.get(id_)
        if obj is not None:
            self.session.delete(obj)
            self.session.commit()


class WorldRepository(BaseRepository):
    model = World
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && uv run pytest tests/persistence/test_repository.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat: BaseRepository 与 WorldRepository

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 11: 仓储 —— 子实体（按 world_id 过滤）

**Files:**
- Modify: `backend/app/persistence/repository.py`
- Test: `backend/tests/persistence/test_repository.py`（追加）

- [ ] **Step 1: 追加失败测试到 `backend/tests/persistence/test_repository.py` 末尾**

```python
from app.models.character import Character
from app.models.event import Event
from app.models.image_asset import ImageAsset
from app.persistence.repository import CharacterRepository, EventRepository, ImageAssetRepository


def _seed_world(session):
    from app.models.world import World
    from app.persistence.repository import WorldRepository

    return WorldRepository(session).create(World(name="w"))


def test_list_characters_by_world(session):
    wid = _seed_world(session)
    repo = CharacterRepository(session)
    repo.create(Character(name="a", world_id=wid))
    repo.create(Character(name="b", world_id=wid))
    repo.create(Character(name="c", world_id="other"))
    rows = repo.list_by_world(wid)
    assert len(rows) == 2


def test_list_events_by_world_ordered_by_tick(session):
    wid = _seed_world(session)
    repo = EventRepository(session)
    repo.create(Event(world_id=wid, tick=2))
    repo.create(Event(world_id=wid, tick=1))
    repo.create(Event(world_id=wid, tick=3))
    rows = repo.list_by_world(wid)
    ticks = [e.tick for e in rows]
    assert ticks == [1, 2, 3]


def test_image_asset_repository(session):
    wid = _seed_world(session)
    repo = ImageAssetRepository(session)
    repo.create(ImageAsset(world_id=wid, prompt="p"))
    assert len(repo.list_by_world(wid)) == 1
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && uv run pytest tests/persistence/test_repository.py -v`
Expected: FAIL，`ImportError: cannot import name CharacterRepository`。

- [ ] **Step 3: 修改 `backend/app/persistence/repository.py`**

在 `BaseRepository` 类中追加一个 `list_by_world` 方法：

```python
    def list_by_world(self, world_id: str, limit: int = 1000, offset: int = 0) -> list[T]:
        """按 world_id 过滤（要求模型有 world_id 字段）。"""
        stmt = (
            select(self.model)
            .where(self.model.world_id == world_id)  # type: ignore[attr-defined]
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.exec(stmt).all())
```

并在文件末尾（`WorldRepository` 之后）追加各子实体仓储。先在顶部 import 段追加：

```python
from app.models.character import Character
from app.models.event import Event
from app.models.image_asset import ImageAsset
from app.models.location import Location
from app.models.memory import Memory
from app.models.relationship import Relationship
from app.models.director import DirectorDirective
```

再在文件末尾追加：

```python
class LocationRepository(BaseRepository):
    model = Location


class CharacterRepository(BaseRepository):
    model = Character


class RelationshipRepository(BaseRepository):
    model = Relationship


class EventRepository(BaseRepository):
    model = Event

    def list_by_world(self, world_id: str, limit: int = 1000, offset: int = 0) -> list[Event]:
        stmt = (
            select(Event)
            .where(Event.world_id == world_id)
            .order_by(Event.tick)
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.exec(stmt).all())


class MemoryRepository(BaseRepository):
    model = Memory


class ImageAssetRepository(BaseRepository):
    model = ImageAsset


class DirectorDirectiveRepository(BaseRepository):
    model = DirectorDirective
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && uv run pytest tests/persistence/test_repository.py -v`
Expected: PASS（所有测试）。

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat: 子实体仓储（按 world_id 过滤，Event 按 tick 排序）

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 12: 图像文件存储

**Files:**
- Create: `backend/app/persistence/image_store.py`
- Test: `backend/tests/persistence/test_image_store.py`

- [ ] **Step 1: 写失败测试 `backend/tests/persistence/test_image_store.py`**

```python
from app.persistence.image_store import ImageStore


def test_save_and_load_image(tmp_path):
    store = ImageStore(base_dir=str(tmp_path))
    data = b"\x89PNG fake image bytes"
    path = store.save(world_id="w1", image_id="img-1", data=data, ext="png")
    assert path.endswith("img-1.png")
    loaded = store.load(path)
    assert loaded == data


def test_save_uses_world_subdir(tmp_path):
    store = ImageStore(base_dir=str(tmp_path))
    path = store.save(world_id="w1", image_id="img-1", data=b"x", ext="png")
    assert "w1" in path


def test_delete_image(tmp_path):
    store = ImageStore(base_dir=str(tmp_path))
    path = store.save(world_id="w1", image_id="img-1", data=b"x", ext="png")
    store.delete(path)
    import pathlib

    assert not pathlib.Path(path).exists()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && uv run pytest tests/persistence/test_image_store.py -v`
Expected: FAIL，`ModuleNotFoundError`。

- [ ] **Step 3: 实现 `backend/app/persistence/image_store.py`**

```python
import os


class ImageStore:
    """把图像字节存到本地文件系统，按 world_id 分目录。"""

    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def _ensure_dir(self, world_id: str) -> str:
        directory = os.path.join(self.base_dir, world_id)
        os.makedirs(directory, exist_ok=True)
        return directory

    def save(self, world_id: str, image_id: str, data: bytes, ext: str = "png") -> str:
        directory = self._ensure_dir(world_id)
        path = os.path.join(directory, f"{image_id}.{ext}")
        with open(path, "wb") as f:
            f.write(data)
        return path

    def load(self, path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    def delete(self, path: str) -> None:
        if os.path.exists(path):
            os.remove(path)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && uv run pytest tests/persistence/test_image_store.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat: 图像文件存储（本地，按 world 分目录）

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 13: World CRUD API

**Files:**
- Create: `backend/app/api/worlds.py`
- Modify: `backend/app/api/router.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/persistence/db.py`
- Test: `backend/tests/api/__init__.py`（空）
- Test: `backend/tests/api/test_worlds.py`

- [ ] **Step 1: 写失败测试 `backend/tests/api/test_worlds.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

# 注册模型
import app.models.world  # noqa
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
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && uv run pytest tests/api/test_worlds.py -v`
Expected: FAIL，`ImportError: cannot import name 'get_session' from 'app.api.deps'` 或 404。

- [ ] **Step 3: 创建 `backend/app/api/deps.py`（session 依赖）**

```python
from typing import Iterator

from sqlalchemy.engine import Engine
from sqlmodel import Session

_engine_instance: Engine | None = None


def set_engine(engine: Engine) -> None:
    """由 main.py 启动时（或测试）注入 engine。"""
    global _engine_instance
    _engine_instance = engine


def get_engine() -> Engine | None:
    return _engine_instance


def get_session() -> Iterator[Session]:
    engine = _engine_instance
    if engine is None:
        raise RuntimeError("DB engine not initialized; call set_engine() first.")
    with Session(engine) as session:
        yield session
```

- [ ] **Step 4: 实现 `backend/app/api/worlds.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.api.deps import get_session
from app.models.world import World
from app.persistence.repository import WorldRepository

router = APIRouter(prefix="/worlds", tags=["worlds"])


def _repo(session: Session = Depends(get_session)) -> WorldRepository:
    return WorldRepository(session)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_world(payload: dict, session: Session = Depends(get_session)) -> World:
    repo = WorldRepository(session)
    return repo.create(World(**payload))


@router.get("")
def list_worlds(session: Session = Depends(get_session)) -> list[World]:
    return WorldRepository(session).list()


@router.get("/{world_id}")
def get_world(world_id: str, session: Session = Depends(get_session)) -> World:
    world = WorldRepository(session).get(world_id)
    if world is None:
        raise HTTPException(status_code=404, detail="World not found")
    return world


@router.delete("/{world_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_world(world_id: str, session: Session = Depends(get_session)) -> None:
    WorldRepository(session).delete(world_id)
```

- [ ] **Step 5: 修改 `backend/app/api/router.py` 挂载 worlds 路由**

```python
from fastapi import APIRouter

from app.api import health, worlds

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(worlds.router)
```

- [ ] **Step 6: 修改 `backend/app/main.py`，启动时初始化 engine**

```python
from fastapi import FastAPI

from app.api.router import api_router
from app.api.deps import set_engine
from app.config import get_settings
from app.persistence.db import create_db_engine, init_db

app = FastAPI(title="Story Dream Factory", version="0.1.0")
app.include_router(api_router)


@app.on_event("startup")
def _startup() -> None:
    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    init_db(engine)
    set_engine(engine)
```

- [ ] **Step 7: 运行测试验证通过**

Run: `cd backend && uv run pytest tests/api/test_worlds.py tests/test_health.py -v`
Expected: PASS（API 测试与健康检查都通过）。

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: World CRUD API + 启动时初始化 DB engine

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 14: LLM 网关 —— LiteLLM 封装 + 结构化输出 + fallback

**Files:**
- Create: `backend/app/llm/__init__.py`（空）
- Create: `backend/app/llm/config.py`
- Create: `backend/app/llm/gateway.py`
- Create: `backend/scripts/check_llm.py`
- Test: `backend/tests/llm/__init__.py`（空）
- Test: `backend/tests/llm/test_gateway.py`

- [ ] **Step 1: 写失败测试 `backend/tests/llm/test_gateway.py`**

```python
import pytest
from unittest.mock import AsyncMock, patch

from app.llm.config import TierConfig, LLMRoutingConfig
from app.llm.gateway import LLMGateway


def _routing() -> LLMRoutingConfig:
    return LLMRoutingConfig(
        tiers={
            "tier1": TierConfig(model="openai/glm-4-plus", fallback_models=[]),
            "tier2": TierConfig(model="openai/glm-4-plus", fallback_models=[]),
        },
        default_tier="tier1",
    )


@pytest.mark.asyncio
async def test_complete_returns_text():
    gw = LLMGateway(_routing())
    fake = AsyncMock(return_value={"content": "hello"})
    with patch("app.llm.gateway.acompletion", fake):
        result = await gw.complete(messages=[{"role": "user", "content": "hi"}])
    assert result == "hello"
    fake.assert_awaited_once()


@pytest.mark.asyncio
async def test_complete_falls_back_on_error():
    gw = LLMGateway(
        LLMRoutingConfig(
            tiers={
                "tier1": TierConfig(
                    model="primary/model", fallback_models=["fallback/model"]
                )
            },
            default_tier="tier1",
        )
    )
    call_count = {"n": 0}

    async def fake_acompletion(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("primary down")
        return {"content": "from fallback"}

    with patch("app.llm.gateway.acompletion", side_effect=fake_acompletion):
        result = await gw.complete(messages=[{"role": "user", "content": "hi"}])
    assert result == "from fallback"
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_complete_json_parses_structured_output():
    gw = LLMGateway(_routing())

    async def fake_acompletion(**kwargs):
        return {"content": '{"intent": "move", "target": "tavern"}'}

    with patch("app.llm.gateway.acompletion", side_effect=fake_acompletion):
        data = await gw.complete_json(
            messages=[{"role": "user", "content": "go"}]
        )
    assert data == {"intent": "move", "target": "tavern"}
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && uv run pytest tests/llm/test_gateway.py -v`
Expected: FAIL，`ModuleNotFoundError`。

- [ ] **Step 3: 实现 `backend/app/llm/config.py`**

```python
from dataclasses import dataclass, field


@dataclass
class TierConfig:
    model: str
    fallback_models: list[str] = field(default_factory=list)


@dataclass
class LLMRoutingConfig:
    tiers: dict[str, TierConfig]
    default_tier: str = "tier1"

    def models_for_tier(self, tier: str) -> list[str]:
        t = self.tiers.get(tier) or self.tiers[self.default_tier]
        return [t.model, *t.fallback_models]
```

- [ ] **Step 4: 实现 `backend/app/llm/gateway.py`**

```python
import json
from typing import Any

from litellm import acompletion

from app.llm.config import LLMRoutingConfig


class LLMGateway:
    """LLM 调用网关：分层路由 + fallback + 结构化输出。

    M1 不真实调用外部 API（测试全部 mock）；真实调用见 scripts/check_llm.py。
    """

    def __init__(self, routing: LLMRoutingConfig):
        self.routing = routing

    async def complete(
        self,
        messages: list[dict],
        tier: str | None = None,
        **kwargs: Any,
    ) -> str:
        tier = tier or self.routing.default_tier
        models = self.routing.models_for_tier(tier)
        last_error: Exception | None = None
        for model in models:
            try:
                resp = await acompletion(model=model, messages=messages, **kwargs)
                return resp["choices"][0]["message"]["content"]
            except Exception as e:  # fallback 链
                last_error = e
        raise RuntimeError(f"All models failed for tier {tier}") from last_error

    async def complete_json(
        self,
        messages: list[dict],
        tier: str | None = None,
        **kwargs: Any,
    ) -> dict:
        kwargs.setdefault("response_format", {"type": "json_object"})
        text = await self.complete(messages, tier=tier, **kwargs)
        return json.loads(text)
```

> 注：真实 litellm 返回的是 `ModelResponse`，`resp["choices"][0]["message"]["content"]` 兼容（litellm 支持下标访问）。测试 mock 直接返回 dict。

- [ ] **Step 5: 创建手动验证脚本 `backend/scripts/check_llm.py`**

```python
"""手动验证 LLM 网关真实调用。需配置 .env 中的密钥。

运行：uv run python scripts/check_llm.py
"""
import asyncio
import os

from litellm import acompletion


async def main():
    model = os.getenv("LLM_TIER1_MODEL", "openai/glm-4-plus")
    resp = await acompletion(
        model=model,
        messages=[{"role": "user", "content": "用一句话介绍你自己。"}],
    )
    print(resp["choices"][0]["message"]["content"])


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 6: 运行测试验证通过**

Run: `cd backend && uv run pytest tests/llm/test_gateway.py -v`
Expected: PASS。

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: LLM 网关（LiteLLM 封装 + 分层路由 + fallback + 结构化输出）

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 15: 生图网关 —— 抽象 + provider + 风格锚注入

**Files:**
- Create: `backend/app/imagegen/__init__.py`（空）
- Create: `backend/app/imagegen/gateway.py`
- Create: `backend/scripts/check_imagegen.py`
- Test: `backend/tests/imagegen/__init__.py`（空）
- Test: `backend/tests/imagegen/test_gateway.py`

- [ ] **Step 1: 写失败测试 `backend/tests/imagegen/test_gateway.py`**

```python
import pytest
from unittest.mock import AsyncMock, patch

from app.imagegen.gateway import ImageGateway, build_prompt


def test_build_prompt_prepends_style_anchor():
    visual_style = {"art_style": "oil-painting", "palette": "dark", "negative_prompt": "blurry"}
    prompt = build_prompt(visual_style=visual_style, subject="艾伦站在酒馆前")
    assert "oil-painting" in prompt
    assert "艾伦站在酒馆前" in prompt
    assert "dark" in prompt


def test_build_prompt_without_style():
    prompt = build_prompt(visual_style={}, subject="一个场景")
    assert "一个场景" in prompt


@pytest.mark.asyncio
async def test_generate_returns_image_bytes():
    gw = ImageGateway(provider="zhipu")
    fake = AsyncMock(return_value=b"fake-png-bytes")
    with patch("app.imagegen.gateway.zhipu_generate", fake):
        data = await gw.generate(prompt="p", seed=42)
    assert data == b"fake-png-bytes"
    fake.assert_awaited_once()
    # 确认 seed 被传入
    assert fake.call_args.kwargs["seed"] == 42


@pytest.mark.asyncio
async def test_generate_unknown_provider_raises():
    gw = ImageGateway(provider="unknown")
    with pytest.raises(ValueError):
        await gw.generate(prompt="p", seed=1)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && uv run pytest tests/imagegen/test_gateway.py -v`
Expected: FAIL，`ModuleNotFoundError`。

- [ ] **Step 3: 实现 `backend/app/imagegen/gateway.py`**

```python
from typing import Any

import httpx

from app.config import get_settings


def build_prompt(visual_style: dict, subject: str) -> str:
    """把世界风格锚作为固定前缀，拼到主体描述前——保证跨阶段风格一致。"""
    parts: list[str] = []
    if visual_style.get("art_style"):
        parts.append(f"画风: {visual_style['art_style']}")
    if visual_style.get("palette"):
        parts.append(f"色调: {visual_style['palette']}")
    if visual_style.get("medium"):
        parts.append(f"媒介: {visual_style['medium']}")
    if visual_style.get("composition"):
        parts.append(f"构图: {visual_style['composition']}")
    style_prefix = "，".join(parts)
    return f"{style_prefix}。{subject}" if style_prefix else subject


async def zhipu_generate(prompt: str, seed: int, **kwargs: Any) -> bytes:
    """智谱 CogView 生图（示例实现，需真实密钥）。

    M1 测试不调用此函数（mock）；真实调用见 scripts/check_imagegen.py。
    """
    settings = get_settings()
    api_key = settings.zhipu_api_key
    model = settings.zhipu_image_model
    # 注意：此处为示例 HTTP 调用结构，实际 endpoint/认证以智谱文档为准。
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://open.bigmodel.cn/api/paas/v4/images/generations",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "prompt": prompt, "seed": seed},
        )
        resp.raise_for_status()
        # 真实返回含图片 URL；这里简化为返回字节（实际应下载 URL）
        data = resp.json()
        img_url = data["data"][0]["url"]
        img = await client.get(img_url)
        return img.content


class ImageGateway:
    """生图网关：风格锚注入 + 种子固定 + 多 provider 抽象。"""

    def __init__(self, provider: str | None = None):
        self.provider = provider or get_settings().imagegen_provider

    async def generate(self, prompt: str, seed: int = 0, **kwargs: Any) -> bytes:
        if self.provider == "zhipu":
            return await zhipu_generate(prompt=prompt, seed=seed, **kwargs)
        raise ValueError(f"Unknown image provider: {self.provider}")
```

- [ ] **Step 4: 创建手动验证脚本 `backend/scripts/check_imagegen.py`**

```python
"""手动验证生图网关真实调用。需配置 ZHIPU_API_KEY。

运行：uv run python scripts/check_imagegen.py
"""
import asyncio
import os

from app.imagegen.gateway import ImageGateway


async def main():
    gw = ImageGateway(provider="zhipu")
    data = await gw.generate(prompt="油画风格，一座笼罩在暴风雨中的中世纪小镇", seed=42)
    out = os.path.join("data", "images", "check.png")
    os.makedirs("data/images", exist_ok=True)
    with open(out, "wb") as f:
        f.write(data)
    print(f"saved {out} ({len(data)} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd backend && uv run pytest tests/imagegen/test_gateway.py -v`
Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: 生图网关（风格锚注入 + 种子 + provider 抽象）

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 16: 全量回归 + README 更新

**Files:**
- Modify: `backend/README.md`

- [ ] **Step 1: 运行全部测试**

Run: `cd backend && uv run pytest -v`
Expected: 全部 PASS（约 30+ 个测试）。

- [ ] **Step 2: 验证应用可启动（不连真实 DB 也能起，但路由可用）**

Run:
```bash
cd backend && uv run python -c "
from app.main import app
from fastapi.testclient import TestClient
# 不触发 startup（无 engine），仅验证路由注册
routes = [r.path for r in app.routes]
assert '/health' in routes
assert '/worlds' in routes
print('routes ok:', [r for r in routes if not r.startswith('/openapi')])
"
```
Expected: 打印包含 `/health`、`/worlds` 的路由列表。

- [ ] **Step 3: 更新 `backend/README.md`，追加 M1 完成状态**

在 `backend/README.md` 末尾追加：

````markdown
## M1 地基已实现

- 领域模型（World/WorldTemplate/Location/Character/Relationship/Event/Memory/ImageAsset/DirectorDirective）
- SQLite 持久化（仓储模式）+ 图像文件存储
- 基础 API：`GET /health`、`World CRUD /worlds`
- LLM 网关（LiteLLM + 分层路由 + fallback + 结构化输出）
- 生图网关（风格锚注入 + 种子 + provider 抽象）

### 手动验证网关（需密钥）

```bash
uv run python scripts/check_llm.py
uv run python scripts/check_imagegen.py
```
````

- [ ] **Step 4: Commit**

```bash
git add backend/
git commit -m "docs: M1 完成——README 更新与全量回归

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## 完成标准

M1 完成后应满足：
1. `uv run pytest` 全绿（领域模型、持久化、API、LLM 网关、生图网关均有测试）。
2. `uv run uvicorn app.main:app` 可启动，`GET /health` 返回 `{"status":"ok"}`。
3. `World CRUD /worlds` 可用（创建/查询/列表/删除）。
4. LLM 网关与生图网关接口可用（mock 测试通过），手动脚本可验证真实调用（需密钥）。
5. 无任何业务逻辑（模拟引擎/Agent/世界构建）——那是 M2+。
