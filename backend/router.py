# backend/router.py
from fastapi import APIRouter

from backend.domains.user_features.combat.api.router import router as combat_router

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
]

api_router.include_router(combat_router, prefix="/combat", tags=["Combat"])
