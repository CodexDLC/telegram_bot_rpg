# app/services/report_service.py
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from loguru import logger as log

from apps.common.core.settings import settings


class ReportService:
    @staticmethod
    async def send_report(bot: Bot, user_id: int, username: str, report_type: str, report_text: str) -> bool:
        """
        Отправить форматированный отчет в административный канал.
        """
        if not settings.bug_report_channel_id:
            log.warning("Отчет не отправлен: BUG_REPORT_CHANNEL_ID не задан.")
            return False

        # Форматирование текста для админов (Markdown)
        message_text = (
            f"🐞 *НОВЫЙ БАГ-РЕПОРТ*\n"
            f"----------------------------------\n"
            f"👤 *Пользователь:* <code>{username}</code> (ID: {user_id})\n"
            f"🏷️ *Категория:* {report_type}\n"
            f"📝 *Текст отчета:*\n"
            f"```\n{report_text[:1000]}\n```"  # Ограничиваем текст
        )

        try:
            await bot.send_message(chat_id=settings.bug_report_channel_id, text=message_text, parse_mode="HTML")
            log.info(f"Отчет от {user_id} ({report_type}) успешно отправлен в канал.")
            return True
        except TelegramAPIError as e:
            log.error(
                f"Критическая ошибка при отправке отчета в канал {settings.bug_report_channel_id}: {e}",
                exc_info=True,
            )
            return False
