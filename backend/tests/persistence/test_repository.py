from app.models.character import Character
from app.models.event import Event
from app.models.image_asset import ImageAsset
from app.models.world import World
from app.persistence.repository import (
    CharacterRepository,
    EventRepository,
    ImageAssetRepository,
    WorldRepository,
)


def _seed_world(session) -> str:
    """创建一个 World 并返回其 id。"""
    return WorldRepository(session).create(World(name="w")).id


def test_create_and_get_world(session):
    repo = WorldRepository(session)
    world = repo.create(World(name="艾尔德兰", vision="v"))
    fetched = repo.get(world.id)
    assert fetched is not None
    assert fetched.name == "艾尔德兰"


def test_list_worlds(session):
    repo = WorldRepository(session)
    repo.create(World(name="a"))
    repo.create(World(name="b"))
    rows = repo.list()
    assert len(rows) == 2


def test_delete_world(session):
    repo = WorldRepository(session)
    world = repo.create(World(name="a"))
    repo.delete(world.id)
    assert repo.get(world.id) is None


def test_update_world(session):
    repo = WorldRepository(session)
    world = repo.create(World(name="a"))
    world.name = "b"
    updated = repo.update(world)
    assert updated.name == "b"


def test_list_characters_by_world(session):
    wid = _seed_world(session)
    repo = CharacterRepository(session)
    repo.create(Character(name="a", world_id=wid))
    repo.create(Character(name="b", world_id=wid))
    repo.create(Character(name="c", world_id="other"))
    rows = repo.list_by_world(wid)
    assert len(rows) == 2


def test_list_events_by_world_ordered_by_tick(session):
    wid = _seed_world(session)
    repo = EventRepository(session)
    repo.create(Event(world_id=wid, tick=2))
    repo.create(Event(world_id=wid, tick=1))
    repo.create(Event(world_id=wid, tick=3))
    rows = repo.list_by_world(wid)
    ticks = [e.tick for e in rows]
    assert ticks == [1, 2, 3]


def test_image_asset_repository(session):
    wid = _seed_world(session)
    repo = ImageAssetRepository(session)
    repo.create(ImageAsset(world_id=wid, prompt="p"))
    assert len(repo.list_by_world(wid)) == 1
