from __future__ import annotations
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api.simulation import _SIMULATORS, _get_llm

router = APIRouter(tags=["websocket"])


@router.websocket("/worlds/{world_id}/ws")
async def world_websocket(websocket: WebSocket, world_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action", "")
            if action == "step":
                sim = None
                for s in _SIMULATORS.values():
                    if s.world.id == world_id:
                        sim = s
                        break
                if sim:
                    events = await sim.tick()
                    await websocket.send_json({
                        "tick": sim.world.clock_tick,
                        "events": [
                            {"tick": e.tick, "type": e.type.value if hasattr(e.type, "value") else str(e.type),
                             "narration": e.narration, "participants": e.participants}
                            for e in events
                        ],
                    })
                else:
                    await websocket.send_json({"error": "no simulation"})
            elif action == "status":
                sim = None
                for s in _SIMULATORS.values():
                    if s.world.id == world_id:
                        sim = s
                        break
                if sim:
                    await websocket.send_json({
                        "tick": sim.world.clock_tick,
                        "total_events": len(sim.event_history),
                    })
            elif action == "disconnect":
                break
    except WebSocketDisconnect:
        pass
