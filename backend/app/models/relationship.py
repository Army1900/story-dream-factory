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
