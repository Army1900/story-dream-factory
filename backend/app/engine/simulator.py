from __future__ import annotations
import asyncio
from app.agents.character_agent import CharacterAgent
from app.agents.narrator import Narrator
from app.agents.proposal import ActionProposal
from app.physics.engine import PhysicsEngine, ResolvedAction
from app.physics.rules import update_relationship
from app.models.world import World
from app.models.character import Character
from app.models.event import Event
from app.models.enums import EventType


class Simulator:
    """模拟引擎（M4 多角色版）：并行决策→物理裁决→叙述。"""

    def __init__(self, world: World, characters: list[Character], llm_gateway,
                 world_dir: str | None = None):
        self.world = world
        self.characters = characters
        self.llm = llm_gateway
        self.narrator = Narrator(llm_gateway)
        self.physics = PhysicsEngine()
        self.agents = [CharacterAgent(c, llm_gateway) for c in characters]
        self.event_history: list[Event] = []
        self.character_memories: dict[str, list] = {}
        self.directives: list[dict] = []
        # 文件系统持久化目录；None 时行为完全不变（向后兼容）
        self.world_dir = world_dir

    def _build_snapshot(self) -> dict:
        locs = {}
        for c in self.characters:
            state = c.state or {}
            loc = state.get("location_id", "未知")
            locs.setdefault(loc, []).append(c.name)
        location = list(locs.keys())[0] if locs else "未知"
        present = [c.name for c in self.characters]
        recent = [e.narration for e in self.event_history[-3:]] if self.event_history else []
        return {"location": location, "present": present, "recent_events": recent, "locations": locs}

    async def tick(self) -> list[Event]:
        current_tick = self.world.clock_tick

        # 处理导演注入（在角色决策前）
        injected_events: list[Event] = []
        while self.directives:
            d = self.directives.pop(0)
            if d["type"] == "inject_event":
                evt = Event(
                    world_id=self.world.id, tick=current_tick,
                    type=EventType.director,
                    participants=[], location_id="",
                    payload=d["payload"],
                    narration=d["payload"].get("description", "导演介入"),
                )
                injected_events.append(evt)
                self.event_history.append(evt)
            elif d["type"] == "set_goal":
                target_name = d.get("target", "")
                for c in self.characters:
                    if c.name == target_name:
                        c.goals = c.goals or {}
                        c.goals.update(d["payload"])
            elif d["type"] == "modify_world":
                key = d["payload"].get("key", "")
                value = d["payload"].get("value")
                if key == "state_flags" and isinstance(value, dict):
                    self.world.state_flags.update(value)
                elif key == "rules" and isinstance(value, list):
                    self.world.rules = value

        snapshot = self._build_snapshot()

        # ① 角色并行决策
        proposals = await asyncio.gather(*[a.decide(snapshot, current_tick=current_tick) for a in self.agents])

        # ② 物理引擎裁决
        resolved_actions: list[ResolvedAction] = []
        for agent, proposal in zip(self.agents, proposals):
            resolved = self.physics.resolve(
                proposal=proposal,
                character_state=dict(agent.character.state or {}),
                world_rules=self.world.rules or [],
            )
            # 应用状态变更到角色
            agent.character.state = resolved.new_state
            resolved_actions.append(resolved)

        # ③ 关系变化（基于行动类型）
        self._update_relationships(resolved_actions)

        # ④ 世界意识叙述（按地点分组：同地点多角色合并为一段连贯场景叙述）
        events: list[Event] = list(injected_events)
        narrated = await self._narrate_grouped(resolved_actions, current_tick)
        for event in narrated:
            events.append(event)
            self.event_history.append(event)

        # ⑤ 记忆写入（从事件提取）
        from app.memory.writer import MemoryWriter
        writer = MemoryWriter()
        char_names = [c.name for c in self.characters]
        if not hasattr(self, 'character_memories'):
            self.character_memories = {}
        for event in events:
            new_mems = writer.extract_memories(event, char_names)
            for m in new_mems:
                self.character_memories.setdefault(m.character_id, []).append(m)

        # ⑥ 修复记忆回路：把累积记忆同步回对应 agent，让下一 tick 能检索到
        # （此前 agent.memories 恒空是 bug）
        for agent in self.agents:
            char_name = agent.character.name
            new_mems = self.character_memories.get(char_name, [])
            agent.memories = new_mems

        # ⑥b 反思（每 interval tick 触发一次，用 LLM 生成高层洞察）
        await self._try_reflect(current_tick)

        self.world.clock_tick += 1

        # ⑦ 文件持久化（仅当 world_dir 已接线）
        if self.world_dir:
            self._persist(current_tick, events)

        return events

    # ----------------------------------------------------------- 持久化辅助
    def _persist(self, current_tick: int, events: list[Event]) -> None:
        """tick 末尾把 events / memories / world 写入文件系统（YAML）。"""
        from app.persistence.world_store import WorldStore
        store = WorldStore()
        wd = self.world_dir

        # events → events/tick-{N:03d}.yaml
        store.save_events(wd, current_tick, [self._event_to_dict(e) for e in events])

        # memories → memories/{name}.yaml（仅有记忆的角色写文件，避免空文件）
        for char_name, mems in self.character_memories.items():
            store.save_memories(wd, char_name, [self._memory_to_dict(m) for m in mems])

        # world → world.yaml（World 字段 + Characters state + clock_tick 推进）
        store.save_world(wd, self._export_world_state())

    def _event_to_dict(self, e) -> dict:
        """Event 对象 → dict。"""
        return {
            "type": e.type.value if hasattr(e.type, "value") else str(e.type),
            "participants": e.participants or [],
            "location_id": e.location_id,
            "narration": e.narration,
            "tick": e.tick,
            "payload": e.payload or {},
        }

    def _memory_to_dict(self, m) -> dict:
        """Memory 对象 → dict。"""
        mtype = getattr(m, "type", "")
        return {
            "type": mtype if isinstance(mtype, str) else mtype.value,
            "content": getattr(m, "content", ""),
            "tick": getattr(m, "tick", 0),
            "importance": getattr(m, "importance", 5.0),
        }

    def _export_world_state(self) -> dict:
        """导出当前世界状态（含 characters / locations / relationships）。"""
        return {
            "id": self.world.id,
            "name": self.world.name,
            "vision": self.world.vision,
            "setting": self.world.setting,
            "rules": self.world.rules or [],
            "visual_style": self.world.visual_style or {},
            "clock_tick": self.world.clock_tick,
            "clock_date": self.world.clock_date,
            "state_flags": self.world.state_flags or {},
            "initial_state": self.world.initial_state or {},
            "characters": [
                {
                    "id": c.id,
                    "name": c.name,
                    "archetype": c.archetype,
                    "personality": c.personality or {},
                    "backstory": c.backstory,
                    "goals": c.goals or {},
                    "state": c.state or {},
                }
                for c in self.characters
            ],
            # Locations / Relationships 当前未作为独立集合存在 Simulator 中，
            # 留空列表以匹配 world.yaml schema（后续 Task 接线时填充）。
            "locations": [],
            "relationships": [],
        }

    async def _try_reflect(self, current_tick: int) -> None:
        """每 interval tick 触发反思：LLM 生成高层洞察，追加到角色记忆。"""
        from app.memory.reflection import Reflector
        reflector = Reflector(self.llm, interval=5, min_memories=5)
        for agent in self.agents:
            char_name = agent.character.name
            mems = self.character_memories.get(char_name, [])
            if not reflector.should_reflect(current_tick, len(mems)):
                continue
            try:
                insight = await reflector.reflect(mems, character_name=char_name, current_tick=current_tick)
                if insight:
                    self.character_memories.setdefault(char_name, []).append(insight)
                    agent.memories = self.character_memories[char_name]
            except Exception:
                pass  # 反思失败不阻塞 tick

    async def _narrate_grouped(self, resolved_actions: list[ResolvedAction], current_tick: int) -> list[Event]:
        """按地点分组叙述。

        - 单角色地点：单独叙述（保持原行为）。
        - 同地点多角色：合并为一段连贯场景叙述，产出一个场景 Event，
          participants 记录在场全部角色（便于记忆写入覆盖每个人）。
        """
        # 按角色移动后的地点分组，保留原始索引以取角色名
        groups: dict[str, list[int]] = {}
        for idx, resolved in enumerate(resolved_actions):
            loc = resolved.new_state.get("location_id", "未知")
            groups.setdefault(loc, []).append(idx)

        events: list[Event] = []
        for loc, idxs in groups.items():
            if len(idxs) == 1:
                idx = idxs[0]
                resolved = resolved_actions[idx]
                event = await self.narrator.narrate(
                    proposal=resolved.proposal,
                    world_name=self.world.name,
                    tick=current_tick,
                    location=loc,
                    world_setting=self.world.setting,
                )
                events.append(event)
                continue

            # 同地点多角色：合并叙述
            proposals = [resolved_actions[i].proposal for i in idxs]
            participants = [self.agents[i].character.name for i in idxs]
            narration = await self.narrator.narrate_group(
                proposals=proposals,
                participants=participants,
                world_name=self.world.name,
                location=loc,
                world_setting=self.world.setting,
            )
            event_type = self._dominant_event_type(proposals)
            events.append(Event(
                world_id=self.world.id,
                tick=current_tick,
                type=event_type,
                participants=participants,
                location_id=loc,
                payload={"scene": [p.to_dict() for p in proposals]},
                narration=narration,
            ))
        return events

    def _dominant_event_type(self, proposals: list[ActionProposal]) -> EventType:
        """从一组行动中选出主导事件类型：冲突 > 对话 > 合作 > 通用行动。"""
        types = [p.action_type for p in proposals]
        if "conflict" in types:
            return EventType.conflict
        if "dialogue" in types:
            return EventType.dialogue
        if "cooperation" in types:
            return EventType.relationship_change
        return EventType.action

    def _update_relationships(self, actions: list[ResolvedAction]) -> None:
        """根据行动类型更新角色间关系（简化版：同地点的角色互相影响）。"""
        for i, act in enumerate(actions):
            if not act.success:
                continue
            atype = act.proposal.action_type
            if atype not in ("conflict", "dialogue", "cooperation"):
                continue
            target_name = act.proposal.target
            if not target_name:
                continue
            # 找目标角色
            for c in self.characters:
                if c.name == target_name:
                    current = (c.state or {}).get("affinity", {}).get(self.agents[i].character.name, 0.0)
                    new_val = update_relationship(current, atype)
                    c.state.setdefault("affinity", {})[self.agents[i].character.name] = new_val
                    break
