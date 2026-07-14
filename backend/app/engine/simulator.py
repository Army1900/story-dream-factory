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


class Simulator:
    """模拟引擎（M4 多角色版）：并行决策→物理裁决→叙述。"""

    def __init__(self, world: World, characters: list[Character], llm_gateway):
        self.world = world
        self.characters = characters
        self.llm = llm_gateway
        self.narrator = Narrator(llm_gateway)
        self.physics = PhysicsEngine()
        self.agents = [CharacterAgent(c, llm_gateway) for c in characters]
        self.event_history: list[Event] = []

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
        snapshot = self._build_snapshot()

        # ① 角色并行决策
        proposals = await asyncio.gather(*[a.decide(snapshot) for a in self.agents])

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

        # ④ 世界意识叙述（批量）
        events: list[Event] = []
        for resolved in resolved_actions:
            event = await self.narrator.narrate(
                proposal=resolved.proposal,
                world_name=self.world.name,
                tick=current_tick,
                location=resolved.new_state.get("location_id", "未知"),
                world_setting=self.world.setting,
            )
            events.append(event)
            self.event_history.append(event)

        self.world.clock_tick += 1
        return events

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
