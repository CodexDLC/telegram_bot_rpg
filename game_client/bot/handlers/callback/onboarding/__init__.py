from aiogram import Router

from .onboarding_handler import router as onboarding_router

onboarding_router_group = Router(name="onboarding_group")
onboarding_router_group.include_router(onboarding_router)
