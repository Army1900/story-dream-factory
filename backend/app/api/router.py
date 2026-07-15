from fastapi import APIRouter

from app.api import builder, director, health, import_world, simulation, websocket, worlds

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(worlds.router)
api_router.include_router(builder.router)
api_router.include_router(import_world.router)
api_router.include_router(simulation.router)
api_router.include_router(director.router)
api_router.include_router(websocket.router)
