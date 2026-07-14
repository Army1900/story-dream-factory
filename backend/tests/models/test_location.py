from app.models.location import Location


def test_location_defaults():
    loc = Location(name="酒馆", world_id="w1")
    assert loc.name == "酒馆"
    assert loc.world_id == "w1"
    assert loc.neighbors == []
    assert loc.occupants == []
    assert loc.resources == []
    assert loc.id


def test_location_with_connections():
    loc = Location(
        name="集市",
        world_id="w1",
        description="喧嚣的集市",
        neighbors=["loc-tavern", "loc-palace"],
        occupants=["char-a", "char-b"],
        resources=["金币", "面包"],
    )
    assert loc.neighbors == ["loc-tavern", "loc-palace"]
    assert len(loc.occupants) == 2
