# apps/bot/ui_service/new_character/onboarding_service.py
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto import CharacterOnboardingUpdateDTO
from backend.database.postgres.repositories.characters_repo_orm import CharactersRepoORM
from backend.database.redis.manager.account_manager import AccountManager
from game_client.bot.resources.keyboards.callback_data import GenderCallback
from game_client.bot.resources.texts.buttons_callback import Buttons
from game_client.bot.resources.texts.game_messages.lobby_messages import LobbyMessages

DEFAULT_SPAWN_POINT = "52_52"


class OnboardingService:
    """
    Сервис для управления процессом создания нового персонажа (onboarding).
    """

    def __init__(self, user_id: int, char_id: int | None = None, account_manager: AccountManager | None = None):
        self.user_id = user_id
        self.buttons = Buttons
        self.new_char = LobbyMessages.NewCharacter
        self.char_id = char_id
        self.account_mgr = account_manager
        log.debug(f"Инициализирован {self.__class__.__name__} для user_id={self.user_id}, char_id={char_id}.")

    def get_data_start_creation_content(self) -> tuple[str, InlineKeyboardMarkup]:
        text = self.new_char.GENDER_CHOICE
        kb = self._start_creation_kb()
        return text, kb

    def get_data_start_gender(self, gender_value: str) -> tuple[str, str]:
        """
        Обрабатывает выбор пола и возвращает данные для следующего шага.
        """
        text = self.new_char.NAME_INPUT
        gender_display = self.buttons.GENDER.get(gender_value, "Не указан")
        return text, gender_display

    async def finalize_character_creation(
        self, session: AsyncSession, char_update_dto: CharacterOnboardingUpdateDTO
    ) -> None:
        if not self.char_id or not self.account_mgr:
            raise ValueError("char_id and account_manager must be set.")
        char_repo = CharactersRepoORM(session)
        try:
            await char_repo.update_character_onboarding(character_id=self.char_id, character_data=char_update_dto)
        except Exception:
            await session.rollback()
            raise
        await self.account_mgr.update_account_fields(self.char_id, {"location_id": DEFAULT_SPAWN_POINT})

    def get_data_start(self, name: str, gender: str) -> tuple[str, InlineKeyboardMarkup]:
        text = self.new_char.FINAL_CONFIRMATION.format(name=name, gender=gender)
        kb = self._tutorial_kb()
        return text, kb

    def _start_creation_kb(self) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        for key, value in self.buttons.GENDER.items():
            kb.button(text=value, callback_data=GenderCallback(action="select", value=key).pack())
        return kb.as_markup()

    def _tutorial_kb(self) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        data = getattr(self.buttons, "TUTORIAL_START_BUTTON", None)
        if data:
            for key, value in data.items():
                kb.button(text=value, callback_data=key)
            kb.adjust(1)
        return kb.as_markup()
