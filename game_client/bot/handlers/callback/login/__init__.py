# app/handlers/callback/login/__init__.py
from aiogram import Router

# from .char_creation import router as char_creation_router # УДАЛЕНО (Заменено на onboarding)
from .lobby import router as lobby_router
from .lobby_character_selection import router as lobby_character_selection_router

# from .login_handler import router as login_handler_router # ОТКЛЮЧЕНО (Refactoring)
from .logout import router as logout_router

login_router_group = Router(name="login_group")

login_router_group.include_routers(
    lobby_router,
    # char_creation_router,
    logout_router,
    lobby_character_selection_router,
    # login_handler_router,
)
