from aiogram.types import User

from apps.common.schemas_dto.user_dto import UserUpsertDTO
from game_client.telegram_bot.base.base_orchestrator import BaseBotOrchestrator
from game_client.telegram_bot.base.view_dto import UnifiedViewDTO
from game_client.telegram_bot.features.commands.client import AuthClient
from game_client.telegram_bot.features.commands.system.ui import StartUI


class StartBotOrchestrator(BaseBotOrchestrator):
    """
    Оркестратор Главного Меню.
    Реализует абстрактный метод render.
    """

    def __init__(self, auth_client: AuthClient, ui_service: StartUI, user: User):
        # Передаем None, так как команда доступна в любом стейте (или без него)
        super().__init__(expected_state=None)
        self.client = auth_client
        self.ui = ui_service
        self.user = user

    async def render(self, user_name: str) -> UnifiedViewDTO:
        """
        Реализация абстрактного метода.
        Превращает имя пользователя (payload) в готовый UI.
        """
        menu_view = self.ui.render_title_screen(user_name)

        return UnifiedViewDTO(menu=menu_view, content=None, clean_history=True)

    async def handle_start(self) -> UnifiedViewDTO:
        """
        Основной метод действия.
        1. Action (Side Effect) -> Core
        2. Render -> UI
        """
        # 1. Action: Sync User
        user_dto = UserUpsertDTO(
            telegram_id=self.user.id,
            first_name=self.user.first_name,
            username=self.user.username,
            last_name=self.user.last_name,
            language_code=self.user.language_code,
            is_premium=bool(self.user.is_premium),
        )
        await self.client.upsert_user(user_dto)

        # 2. Render
        user_name = self.user.first_name or "Wanderer"
        return await self.render(user_name)

    async def handle_logout(self) -> UnifiedViewDTO:
        """
        Обрабатывает команду выхода.
        Очищает сессию и возвращает на стартовый экран.
        """
        # 1. Очистка сессии на бэкенде
        await self.client.logout(self.user.id)

        # 2. Сброс сцены (через Director, если он установлен, или просто рендер старта)
        if self._director:
            await self._director.state.clear()

        # 3. Рендер стартового экрана
        user_name = self.user.first_name or "Wanderer"
        return await self.render(user_name)
