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
