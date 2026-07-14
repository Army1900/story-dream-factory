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
