from __future__ import annotations
from app.agents.character_agent import CharacterAgent
from app.agents.narrator import Narrator
from app.models.world import World
from app.models.character import Character
from app.models.event import Event


class Simulator:
    """模拟引擎（M3 单角色版）：角色决策→叙述者叙述→写回。"""

    def __init__(self, world: World, characters: list[Character], llm_gateway):
        self.world = world
        self.characters = characters
        self.llm = llm_gateway
        self.narrator = Narrator(llm_gateway)
        self.agents = [CharacterAgent(c, llm_gateway) for c in characters]
        self.event_history: list[Event] = []

    def _build_snapshot(self) -> dict:
        """构建角色可感知的世界快照。"""
        locs = set()
        present = []
        for c in self.characters:
            state = c.state or {}
            loc = state.get("location_id", "未知")
            locs.add(loc)
            present.append(c.name)
        location = locs.pop() if locs else "未知"
        recent = [e.narration for e in self.event_history[-3:]] if self.event_history else []
        return {
            "location": location,
            "present": present,
            "recent_events": recent,
        }

    async def tick(self) -> list[Event]:
        """推进一个 tick：角色决策→叙述→写回。"""
        current_tick = self.world.clock_tick
        snapshot = self._build_snapshot()
        events: list[Event] = []

        for agent in self.agents:
            proposal = await agent.decide(snapshot)
            event = await self.narrator.narrate(
                proposal=proposal,
                world_name=self.world.name,
                tick=current_tick,
                location=snapshot["location"],
                world_setting=self.world.setting,
            )
            events.append(event)
            self.event_history.append(event)

        self.world.clock_tick += 1
        return events
