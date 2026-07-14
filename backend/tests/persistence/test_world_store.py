"""WorldStore 测试：纯 YAML 文件 I/O，不碰 DB。"""

from app.persistence.world_store import WorldStore


def test_save_load_world(tmp_path):
    """world.yaml 存取往返（YAML 格式）。"""
    store = WorldStore()
    world_dir = tmp_path / "艾尔德兰"
    payload = {
        "name": "艾尔德兰",
        "vision": "魔法衰落的王国",
        "rules": ["魔法稀有", "暴力通缉"],
        "clock_tick": 12,
        "characters": [{"id": "c1", "name": "艾伦"}],
    }
    store.save_world(str(world_dir), payload)
    assert (world_dir / "world.yaml").exists()

    loaded = store.load_world(str(world_dir))
    assert loaded == payload


def test_load_nonexistent_returns_none(tmp_path):
    """读不存在的世界返回 None。"""
    store = WorldStore()
    assert store.load_world(str(tmp_path / "nope")) is None


def test_save_load_events(tmp_path):
    """多 tick 事件文件按 tick 升序合并。"""
    store = WorldStore()
    world_dir = tmp_path / "w1"

    # 故意乱序写入，验证排序
    store.save_events(str(world_dir), tick=2, events=[{"narration": "c", "tick": 2}])
    store.save_events(str(world_dir), tick=0, events=[{"narration": "a", "tick": 0}])
    store.save_events(
        str(world_dir),
        tick=1,
        events=[{"narration": "b1", "tick": 1}, {"narration": "b2", "tick": 1}],
    )

    # 文件名格式正确（3 位补零，.yaml 后缀）
    assert (world_dir / "events" / "tick-000.yaml").exists()
    assert (world_dir / "events" / "tick-001.yaml").exists()
    assert (world_dir / "events" / "tick-002.yaml").exists()

    events = store.load_all_events(str(world_dir))
    assert [e["narration"] for e in events] == ["a", "b1", "b2", "c"]


def test_load_events_nonexistent_returns_empty(tmp_path):
    """events/ 不存在时返回空列表。"""
    store = WorldStore()
    assert store.load_all_events(str(tmp_path / "w1")) == []


def test_save_load_memories(tmp_path):
    """角色记忆存取。"""
    store = WorldStore()
    world_dir = tmp_path / "w1"
    mems = [
        {"type": "observation", "content": "艾伦进入酒馆", "tick": 0, "importance": 5.0},
        {"type": "observation", "content": "遇到贝拉", "tick": 1, "importance": 7.0},
    ]
    store.save_memories(str(world_dir), "艾伦", mems)
    assert (world_dir / "memories" / "艾伦.yaml").exists()

    loaded = store.load_memories(str(world_dir), "艾伦")
    assert loaded == mems


def test_load_memories_nonexistent_returns_empty(tmp_path):
    store = WorldStore()
    assert store.load_memories(str(tmp_path / "w1"), "不存在的角色") == []


def test_save_load_directives(tmp_path):
    """导演指令存取。"""
    store = WorldStore()
    world_dir = tmp_path / "w1"
    directives = [
        {"type": "inject_event", "payload": {"description": "暴雨倾盆"}, "target": ""},
        {"type": "set_goal", "payload": {"short_term": "复仇"}, "target": "艾伦"},
    ]
    store.save_directives(str(world_dir), directives)
    assert (world_dir / "directives.yaml").exists()

    loaded = store.load_directives(str(world_dir))
    assert loaded == directives


def test_load_directives_nonexistent_returns_empty(tmp_path):
    store = WorldStore()
    assert store.load_directives(str(tmp_path / "w1")) == []


def test_list_worlds(tmp_path):
    """扫描 worlds/ 下含 world.yaml 的子目录名，已排序。"""
    store = WorldStore()
    worlds_root = tmp_path / "worlds"
    worlds_root.mkdir()
    # 只有含 world.yaml 的目录应被列出
    (worlds_root / "艾尔德兰").mkdir()
    store.save_world(str(worlds_root / "艾尔德兰"), {"name": "艾尔德兰"})
    (worlds_root / "北境").mkdir()
    store.save_world(str(worlds_root / "北境"), {"name": "北境"})
    # 空目录（无 world.yaml）不应被列出
    (worlds_root / "未初始化").mkdir()
    # 普通文件不应被列出
    (worlds_root / "README.md").write_text("hi", encoding="utf-8")

    names = store.list_worlds(str(worlds_root))
    assert names == ["北境", "艾尔德兰"]


def test_list_worlds_nonexistent_root_returns_empty(tmp_path):
    store = WorldStore()
    assert store.list_worlds(str(tmp_path / "nope")) == []


def test_delete_world(tmp_path):
    """删除世界目录（含子文件）。"""
    store = WorldStore()
    world_dir = tmp_path / "w1"
    store.save_world(str(world_dir), {"name": "w1"})
    store.save_events(str(world_dir), tick=0, events=[{"narration": "x"}])
    assert world_dir.exists()

    store.delete_world(str(world_dir))
    assert not world_dir.exists()

    # 删除不存在的目录静默通过
    store.delete_world(str(world_dir))


def test_world_exists(tmp_path):
    """world_exists 以 world.yaml 是否存在为准。"""
    store = WorldStore()
    world_dir = tmp_path / "w1"
    assert store.world_exists(str(world_dir)) is False
    store.save_world(str(world_dir), {"name": "w1"})
    assert store.world_exists(str(world_dir)) is True


def test_yaml_is_human_readable(tmp_path):
    """读回文本，确认是 YAML 格式（block 风格、无 JSON 花括号）。"""
    store = WorldStore()
    world_dir = tmp_path / "w1"
    payload = {
        "name": "艾尔德兰",
        "vision": "魔法衰落的王国",
        "rules": ["魔法稀有", "暴力通缉"],
        "clock_tick": 12,
    }
    store.save_world(str(world_dir), payload)

    raw = (world_dir / "world.yaml").read_text(encoding="utf-8")

    # YAML block 风格：键值用 "key: value"，不是 JSON 的花括号
    assert "name: 艾尔德兰" in raw
    assert "clock_tick: 12" in raw
    # 无 JSON 风格的花括号 / 方括号包裹（block 风格下顶层与对象均不用 {}）
    assert "{" not in raw
    assert "}" not in raw
