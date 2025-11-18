# app/handlers/callback/ui/status_menu/__init__.py
from aiogram import Router

from .character_modifier import router as status_character_modifier_router
from .character_skill import router as status_character_skill_router

# Импортируем роутеры из этой же папки
from .character_status import router as status_character_menu_router

# Создаем "групповой" роутер для меню статуса
status_menu_router_group = Router(name="status_menu_group")

# Собираем "цепочку"
status_menu_router_group.include_routers(
    status_character_menu_router, status_character_skill_router, status_character_modifier_router
)
