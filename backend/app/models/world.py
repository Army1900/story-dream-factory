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
