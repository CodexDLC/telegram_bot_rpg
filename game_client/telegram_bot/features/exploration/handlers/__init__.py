from aiogram import Router

from .interaction_handlers import router as interaction_router
from .list_handlers import router as list_router
from .navigation_handlers import router as navigation_router

router = Router(name="exploration_feature_router")

router.include_router(navigation_router)
router.include_router(interaction_router)
router.include_router(list_router)
