import asyncio
import logging


from app.core.bot_factory import build_app
from app.core.config import BOT_TOKEN
from app.core.log_setup import setup_logging
from app.handlers import router

from database.session import create_db_tables as create_tables


setup_logging(level="DEBUG", to_file=True)



async def main()-> None:
    log = logging.getLogger(__name__)
    log.info("Инициализация базы данных...")
    await create_tables()
    log.info("Инициализация базы данных завершена.")

    if BOT_TOKEN is not None:
        bot, dp = build_app(token=BOT_TOKEN)
        log.info("Бот создан")
        dp.include_router(router)
        log.info("Бот стартует")
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
