# apps/bot/handlers/callback/game/exploration/__init__.py
from aiogram import Router

from .encounter_handlers import router as encounter_router

exploration_router_group = Router(name="exploration_group")
exploration_router_group.include_router(encounter_router)
