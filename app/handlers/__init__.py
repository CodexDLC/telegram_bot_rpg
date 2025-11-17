# app/handlers/__init__.py
from aiogram import Router

# --- Базовые роутеры (которые не в группах) ---
from .commands import router as command_router
from .common_fsm_handlers import router as common_fsm_router
from .bug_report import router as bug_report_router

# --- Наши новые "Цепочки" (Группы) ---
from .callback.login import login_router_group
from .callback.tutorial import tutorial_router_group
from .callback.ui.status_menu import status_menu_router_group


# --- Главный роутер приложения ---
router = Router()

# Регистрируем "цепочки"
router.include_routers(
    # Сначала "общие" хэндлеры
    command_router,
    bug_report_router,

    # Затем "цепочки" callback-хэндлеров
    login_router_group,
    tutorial_router_group,
    status_menu_router_group,

    # 'common_fsm_handlers' (с F.text) должен идти в самом конце,
    # чтобы не перехватывать FSM-текст (например, ввод имени)
    common_fsm_router
)