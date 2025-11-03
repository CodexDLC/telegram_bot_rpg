from aiogram import Router

from .callback.login.lobby import router as lobby_router
from .callback.ui.status_menu.character_status import router as character_status_menu_router
from .callback.ui.status_menu.character_skill import router as character_skill_router
from .fsn_callback.char_creation import router as char_creation_router
from .fsn_callback.tutorial_game import router as tutorial_game_router
from .fsn_callback.lobby_character_selection import router as lobby_character_selection_router

from .commands import router as command_router
from .common_fsm_handlers import router as common_fsm_router


router = Router()



router.include_routers(
    command_router,
    lobby_router,
    char_creation_router,
    tutorial_game_router,
    lobby_character_selection_router,
    character_status_menu_router,
    character_skill_router,
    common_fsm_router
)