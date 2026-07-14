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
