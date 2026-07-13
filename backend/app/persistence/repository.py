from __future__ import annotations

from typing import Generic, Type, TypeVar

from sqlmodel import Session, SQLModel, select

from app.models.world import World
from app.models.location import Location
from app.models.character import Character
from app.models.relationship import Relationship
from app.models.event import Event
from app.models.memory import Memory
from app.models.image_asset import ImageAsset
from app.models.director import DirectorDirective

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

    def list_by_world(
        self, world_id: str, limit: int = 1000, offset: int = 0
    ) -> list[T]:
        """按 world_id 过滤（要求模型有 world_id 字段）。"""
        stmt = (
            select(self.model)
            .where(self.model.world_id == world_id)  # type: ignore[attr-defined]
            .offset(offset)
            .limit(limit)
        )
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


class LocationRepository(BaseRepository):
    model = Location


class CharacterRepository(BaseRepository):
    model = Character


class RelationshipRepository(BaseRepository):
    model = Relationship


class EventRepository(BaseRepository):
    model = Event

    def list_by_world(
        self, world_id: str, limit: int = 1000, offset: int = 0
    ) -> list[Event]:
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
