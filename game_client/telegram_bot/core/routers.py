# game_client/telegram_bot/core/routers.py
"""
Централизованный реестр роутеров для Telegram Bot.
Аналог Django urls.py - все роутеры регистрируются здесь.
"""

from aiogram import Router

# --- Account (Lobby, Onboarding) ---
from game_client.telegram_bot.features.account import handlers as account_handlers

# --- Game Features ---
from game_client.telegram_bot.features.combat.handlers.combat_handlers import router as combat_router

# --- System Commands ---
from game_client.telegram_bot.features.commands import handlers as commands_handlers
from game_client.telegram_bot.features.scenario.handlers.scenario_handler import router as scenario_router

# --- Common Services ---
from game_client.telegram_bot.services.fsm.common_fsm_handlers import router as common_fsm_router

# Главный роутер приложения
main_router = Router(name="main_router")

# --- Регистрация роутеров ---
# Порядок важен: сначала системные, потом игровые фичи, последним - garbage collector
main_router.include_routers(
    # System
    commands_handlers.router,
    # Account
    account_handlers.router,
    # Game Features
    combat_router,
    scenario_router,
    # Common Services (последним чтобы не перехватывал текст раньше времени)
    common_fsm_router,
)
