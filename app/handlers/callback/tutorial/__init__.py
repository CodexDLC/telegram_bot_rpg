# app/handlers/callback/tutorial/__init__.py
from aiogram import Router

# Импортируем роутеры из этой же папки
from .tutorial_game import router as tutorial_game_router
from .tutorial_skill import router as tutorial_skill_router

# Создаем "групповой" роутер для туториала
tutorial_router_group = Router(name="tutorial_group")

# Собираем "цепочку"
tutorial_router_group.include_routers(
    tutorial_game_router,
    tutorial_skill_router
)