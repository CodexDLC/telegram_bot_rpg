# app/handlers/callback/game/arena/__init__.py

from aiogram import Router

# Импортируем роутеры из этой же папки
from .arena_1v1 import router as arena_1v1_router
from .arena_group import router as arena_group_router
from .arena_main import router as arena_main_router
from .arena_tournament import router as arena_tournament_router

# Создаем "групповой" роутер для Арены
arena_router_group = Router(name="arena_group")

# Собираем все роутеры Арены в одну группу
arena_router_group.include_routers(arena_main_router, arena_1v1_router, arena_group_router, arena_tournament_router)
