# game_client/telegram_bot/core/routers.py
"""
Централизованный реестр роутеров для Telegram Bot.
Аналог Django urls.py - все роутеры регистрируются здесь.
"""

from aiogram import Router

# --- Common Services ---
from game_client.telegram_bot.common.services.common_fsm_handlers import router as common_fsm_router

# --- Game Features ---
from game_client.telegram_bot.features.combat.handlers.combat_handlers import router as combat_router

# --- System Commands ---
from game_client.telegram_bot.features.commands.handlers.router import router as commands_router

# from game_client.telegram_bot.features.arena.handlers.arena_handlers import router as arena_router  # TODO
# from game_client.telegram_bot.features.exploration.handlers.exploration_handlers import router as exploration_router  # TODO
# from game_client.telegram_bot.features.inventory.handlers.inventory_handlers import router as inventory_router  # TODO

# Главный роутер приложения
main_router = Router(name="main_router")

# --- Регистрация роутеров ---
# Порядок важен: сначала системные, потом игровые фичи, последним - garbage collector
main_router.include_routers(
    # System
    commands_router,
    # Game Features
    combat_router,
    # arena_router,  # TODO
    # exploration_router,  # TODO
    # inventory_router,  # TODO
    # Common Services (последним чтобы не перехватывал текст раньше времени)
    common_fsm_router,
)
