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
