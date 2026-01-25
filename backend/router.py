# backend/router.py
from fastapi import APIRouter

from backend.domains.user_features.combat.api.router import router as combat_router
from backend.domains.user_features.scenario.api.scenario import router as scenario_router

api_router = APIRouter()

# Описание тегов для Swagger
tags_metadata = [
    {
        "name": "System",
        "description": "Health check and system info.",
    },
    {
        "name": "Combat",
        "description": "Combat system operations.",
    },
    {
        "name": "Scenario",
        "description": "Quest and dialogue system.",
    },
]

api_router.include_router(combat_router, prefix="/combat", tags=["Combat"])
api_router.include_router(scenario_router)  # prefix уже задан внутри scenario.py
