# app/handlers/__init__.py
from aiogram import Router

from .admin.admin_menu import router as admin_router
from .bug_report import router as bug_report_router
from .callback.game import game_router_group

# --- Наши новые "Цепочки" (Группы) ---
from .callback.login import login_router_group
from .callback.onboarding import onboarding_router_group  # <--- НОВЫЙ РОУТЕР
from .callback.tutorial import tutorial_router_group
from .callback.ui.inventory import inventory_group_router
from .callback.ui.menu_dispatch import router as menu_dispatch_router
from .callback.ui.status_menu import status_menu_router_group

# --- Базовые роутеры (которые не в группах) ---
from .commands import router as command_router
from .common_fsm_handlers import router as common_fsm_router

# --- Главный роутер приложения ---
router = Router()

# Регистрируем "цепочки"
router.include_routers(
    # Сначала "общие" хэндлеры
    command_router,
    admin_router,
    bug_report_router,
    menu_dispatch_router,
    # Затем "цепочки" callback-хэндлеров
    login_router_group,
    onboarding_router_group,  # <--- РЕГИСТРАЦИЯ
    tutorial_router_group,
    status_menu_router_group,
    inventory_group_router,
    game_router_group,
    # 'common_fsm_handlers' (с F.text) должен идти в самом конце,
    # чтобы не перехватывать FSM-текст (например, ввод имени)
    common_fsm_router,
)
