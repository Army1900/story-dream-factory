from fastapi import APIRouter

from app.api import builder, director, health, simulation, worlds

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(worlds.router)
api_router.include_router(builder.router)
api_router.include_router(simulation.router)
api_router.include_router(director.router)
