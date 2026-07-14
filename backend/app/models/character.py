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
