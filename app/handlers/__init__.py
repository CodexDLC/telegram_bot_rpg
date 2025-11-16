from aiogram import Router

from .callback.login.lobby import router as lobby_router
from .callback.ui.status_menu.character_status import router as status_character_menu_router
from .callback.ui.status_menu.character_skill import router as status_character_skill_router
from .callback.ui.status_menu.character_modifier import router as status_character_modifier_router
from .callback.tutorial.tutorial_skill import router as tutorial_skill_router
from .callback.login.logout import router as logout_router
from app.handlers.callback.login.char_creation import router as char_creation_router
from app.handlers.callback.tutorial.tutorial_game import router as tutorial_game_router
from app.handlers.callback.login.lobby_character_selection import router as lobby_character_selection_router


from .commands import router as command_router
from .common_fsm_handlers import router as common_fsm_router


from .bug_report import router as bug_report_router

router = Router()



router.include_routers(
    command_router,
    lobby_router,
    char_creation_router,
    tutorial_game_router,
    tutorial_skill_router,
    lobby_character_selection_router,
    status_character_menu_router,
    status_character_skill_router,
    logout_router,
    status_character_modifier_router,
    bug_report_router,
    common_fsm_router
)