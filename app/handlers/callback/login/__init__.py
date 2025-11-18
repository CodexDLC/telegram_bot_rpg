# app/handlers/callback/login/__init__.py
from aiogram import Router

from .char_creation import router as char_creation_router

# Импортируем роутеры из этой же папки
from .lobby import router as lobby_router
from .lobby_character_selection import router as lobby_character_selection_router
from .logout import router as logout_router

# Создаем "групповой" роутер для всей логики логина
login_router_group = Router(name="login_group")

# Собираем "цепочку"
login_router_group.include_routers(lobby_router, char_creation_router, logout_router, lobby_character_selection_router)
