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
