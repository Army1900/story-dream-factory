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
