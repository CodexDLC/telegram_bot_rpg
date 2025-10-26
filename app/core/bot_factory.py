# app/core/bot_factory.py


from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage


def build_app(token: str ) -> tuple[Bot, Dispatcher]:
    bot = Bot(token)
    dp = Dispatcher(storage=MemoryStorage())
    return bot, dp
