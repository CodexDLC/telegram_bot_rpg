from aiogram import Router


from .commands import router as command_router

router = Router()


router.include_routers(
    command_router,
)