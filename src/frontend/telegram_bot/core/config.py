from loguru import logger as log

from src.shared.core.config import CommonSettings


class BotSettings(CommonSettings):
    """
    Настройки для Telegram Bot.
    Добавляет Bot Token и специфичные для бота параметры.
    """

    # --- Bot ---
    bot_token: str

    # --- Channels & Admins ---
    bug_report_channel_id: int | None = None
    admin_ids: str = ""

    # --- Backend API ---
    backend_api_url: str = "http://localhost:8000"
    backend_api_key: str | None = None
    backend_api_timeout: float = 10.0

    @property
    def admin_ids_list(self) -> list[int]:
        """Парсит строку '123,456' в список чисел."""
        if not self.admin_ids:
            return []
        try:
            return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]
        except ValueError:
            log.warning(f"BotSettings | Failed to parse ADMIN_IDS='{self.admin_ids}'. Check .env format.")
            return []
