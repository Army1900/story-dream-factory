"""文件系统持久化：一世界一目录的 YAML 读写。

不依赖 SQLModel/Session，纯 YAML 文件 I/O。所有方法接收 ``world_dir``
（str 或 Path），由调用方决定世界目录的物理位置（通常为 ``worlds/{name}``）。

目录结构::

    {world_dir}/
      world.yaml              ← 世界全貌（World 字段 + Characters + Locations + Relationships）
      events/
        tick-000.yaml         ← [{type, narration, participants, location_id, tick}, ...]
        tick-001.yaml
      memories/
        {char_name}.yaml      ← [{type, content, tick, importance}, ...]
      directives.yaml         ← [{type, payload, target}, ...]
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import yaml


_TICK_RE = re.compile(r"tick-(\d+)\.yaml$")


def _write_yaml(path: Path, data) -> None:
    """把 data 以 UTF-8 YAML 写入 path，自动创建父目录。

    使用 block 风格、保留键序、允许 Unicode，保证人类可读。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(
            data,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )


def _read_yaml(path: Path):
    """读取 YAML 文件；不存在返回 None。"""
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class WorldStore:
    """一世界一目录的 YAML 文件读写。"""

    # ---------------------------------------------------------------- world.yaml
    def save_world(self, world_dir, world_dict: dict) -> None:
        """把世界全貌写入 ``world.yaml``。"""
        _write_yaml(Path(world_dir) / "world.yaml", world_dict)

    def load_world(self, world_dir) -> dict | None:
        """读取 ``world.yaml``；不存在返回 None。"""
        return _read_yaml(Path(world_dir) / "world.yaml")

    # ------------------------------------------------------------------- events/
    def save_events(self, world_dir, tick: int, events: list[dict]) -> None:
        """把某个 tick 的事件列表写入 ``events/tick-{N:03d}.yaml``。"""
        _write_yaml(
            Path(world_dir) / "events" / f"tick-{int(tick):03d}.yaml", events
        )

    def load_all_events(self, world_dir) -> list[dict]:
        """扫描 ``events/`` 目录，返回按 tick 升序排序的扁平事件列表。

        不存在或为空时返回 ``[]``。同一 tick 文件内的事件保持原顺序。
        """
        events_dir = Path(world_dir) / "events"
        if not events_dir.exists():
            return []

        # 收集 (tick_index, 文件内序号, dict) 三元组用于稳定排序
        bucket: list[tuple[int, int, dict]] = []
        for fp in events_dir.glob("tick-*.yaml"):
            m = _TICK_RE.search(fp.name)
            if not m:
                continue
            tick_idx = int(m.group(1))
            items = yaml.safe_load(fp.read_text(encoding="utf-8")) or []
            for i, item in enumerate(items):
                bucket.append((tick_idx, i, item))

        bucket.sort(key=lambda x: (x[0], x[1]))
        return [item for _, _, item in bucket]

    # ------------------------------------------------------------------ memories/
    def save_memories(self, world_dir, char_name: str, memories: list[dict]) -> None:
        """把某角色的记忆写入 ``memories/{char_name}.yaml``。"""
        _write_yaml(Path(world_dir) / "memories" / f"{char_name}.yaml", memories)

    def load_memories(self, world_dir, char_name: str) -> list[dict]:
        """读取某角色的记忆；不存在返回 ``[]``。"""
        data = _read_yaml(Path(world_dir) / "memories" / f"{char_name}.yaml")
        return data or []

    # -------------------------------------------------------------- directives.yaml
    def save_directives(self, world_dir, directives: list[dict]) -> None:
        """把待执行导演指令写入 ``directives.yaml``。"""
        _write_yaml(Path(world_dir) / "directives.yaml", directives)

    def load_directives(self, world_dir) -> list[dict]:
        """读取导演指令；不存在返回 ``[]``。"""
        data = _read_yaml(Path(world_dir) / "directives.yaml")
        return data or []

    # -------------------------------------------------------------- story_state.yaml
    def save_story_state(self, world_dir, state: dict) -> None:
        """把戏剧状态（叙事弧/悬念/张力/摘要）写入 ``story_state.yaml``。"""
        _write_yaml(Path(world_dir) / "story_state.yaml", state)

    def load_story_state(self, world_dir) -> dict | None:
        """读取 ``story_state.yaml``；不存在返回 None。"""
        return _read_yaml(Path(world_dir) / "story_state.yaml")

    # ------------------------------------------------------------------- listing
    def list_worlds(self, worlds_dir) -> list[str]:
        """扫描 ``worlds_dir`` 下所有含 ``world.yaml`` 的子目录名，返回排序后的列表。"""
        root = Path(worlds_dir)
        if not root.exists():
            return []
        names = [
            p.name for p in root.iterdir() if p.is_dir() and (p / "world.yaml").exists()
        ]
        return sorted(names)

    def delete_world(self, world_dir) -> None:
        """删除整个世界目录；不存在则静默忽略。"""
        path = Path(world_dir)
        if path.exists():
            shutil.rmtree(path)

    def world_exists(self, world_dir) -> bool:
        """判断 ``world.yaml`` 是否存在。"""
        return (Path(world_dir) / "world.yaml").exists()
