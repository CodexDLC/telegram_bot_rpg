# app/services/ui_service/lobby_service.py

from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, User
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.keyboards.callback_data import LobbySelectionCallback
from app.resources.schemas_dto.character_dto import CharacterReadDTO, CharacterShellCreateDTO
from app.resources.texts.buttons_callback import Buttons
from app.services.helpers_module.dto_helper import fsm_store
from app.services.ui_service.base_service import BaseUIService
from app.services.ui_service.helpers_ui.lobby_formatters import LobbyFormatter
from database.repositories import get_character_repo
from database.repositories.ORM.characters_repo_orm import CharactersRepoORM


class LobbyService(BaseUIService):
    """
    Сервис для управления UI-логикой лобби выбора персонажей.

    Инкапсулирует операции, связанные с отображением списка персонажей,
    созданием клавиатур и взаимодействием с БД для создания персонажей.
    """

    def __init__(
        self,
        user: User,
        state_data: dict[str, Any],  # Теперь state_data обязателен
        char_id: int | None = None,
    ):
        """
        Инициализирует сервис лобби.
        """

        safe_state_data = state_data

        safe_char_id = char_id or 0

        super().__init__(safe_char_id, safe_state_data)

        # А уже ПОСЛЕ этого устанавливаем свои свойства
        self.user_id = user.id
        self.char_id: int = safe_char_id  # self.char_id МОЖЕТ быть None, это нормально

        log.debug(f"Инициализирован {self.__class__.__name__} для user_id={self.user_id}.")

    def get_message_delete(self, char_name: str) -> tuple[str, InlineKeyboardMarkup]:
        text = f"⚠️ Вы уверены, что хотите удалить персонажа <b>{char_name}</b>?\n\nЭто действие необратимо."

        kb = self._kb_delete()

        return text, kb

    def _kb_delete(self) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()

        yes_b = LobbySelectionCallback(action="delete_yes", char_id=self.char_id).pack()

        no_b = LobbySelectionCallback(action="delete_no", char_id=self.char_id).pack()

        kb.button(text="Да", callback_data=yes_b)
        kb.button(text="Нет", callback_data=no_b)

        kb.adjust(2)

        return kb.as_markup()

    def get_data_lobby_start(
        self, characters: list[CharacterReadDTO] | None = None
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Подготавливает данные для отображения стартового экрана лобби.

        Returns:
            Tuple[str, InlineKeyboardMarkup]: Кортеж с текстом и клавиатурой.
        """
        log.debug(f"Подготовка стартового экрана лобби для user_id={self.user_id}.")
        text = LobbyFormatter.format_character_list(characters)
        kb = self._get_character_lobby_kb(characters)
        return text, kb

    def _get_character_lobby_kb(
        self, characters: list[CharacterReadDTO] | None, max_slots: int = 4
    ) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру для лобби выбора персонажа.

        Args:
            max_slots (int): Максимальное количество слотов для персонажей.

        Returns:
            InlineKeyboardMarkup: Готовая клавиатура для лобби.
        """
        log.debug(f"Создание клавиатуры лобби для user_id={self.user_id}.")
        kb = InlineKeyboardBuilder()
        lobby_buttons = Buttons.LOBBY_KB_UP

        itera_char = len(characters) if characters is not None else 0

        # Создаем кнопки для существующих персонажей.
        if characters:
            for i in range(max_slots):
                if i < itera_char:
                    char = characters[i]
                    callback = LobbySelectionCallback(action="select", char_id=char.character_id)
                    text = f"✅ {char.name}" if char.character_id == self.char_id else f"👤 {char.name}"
                    kb.button(text=text, callback_data=callback.pack())
                else:
                    callback = LobbySelectionCallback(
                        action="create",
                    )
                    # Если слот пуст, добавляем кнопку создания.
                    kb.button(text=lobby_buttons["create"], callback_data=callback.pack())
        else:
            for _ in range(max_slots):
                callback = LobbySelectionCallback(
                    action="create",
                )
                kb.button(text=lobby_buttons["create"], callback_data=callback.pack())

        kb.adjust(2, 2)

        buttons = self._down_button()
        for button in buttons:
            kb.row(button)

        log.debug("Клавиатура лобби успешно создана.")
        return kb.as_markup()

    def _down_button(self) -> list[InlineKeyboardButton]:
        # Допустим, ты передаешь нужные данные как словарь, где ключ - это action
        lobby_buttons_dawn = Buttons.LOBBY_KB_DOWN
        buttons = []

        for key, value in lobby_buttons_dawn.items():
            buttons.append(
                InlineKeyboardButton(
                    text=value,
                    callback_data=LobbySelectionCallback(action=key, char_id=self.char_id).pack(),
                )
            )

        return buttons

    async def create_und_get_character_id(self, session: AsyncSession) -> int:
        """
        Создает "оболочку" персонажа в БД и возвращает его ID.

        "Оболочка" - это минимальная запись, создаваемая до ввода имени/пола.
        Использует собственную сессию для выполнения этой изолированной операции.

        Returns:
            int: ID созданного персонажа.
        """
        log.info(f"Запрос на создание 'оболочки' персонажа для user_id={self.user_id}.")
        dto_object = CharacterShellCreateDTO(user_id=self.user_id)
        char_repo = CharactersRepoORM(session)
        try:
            char_id = await char_repo.create_character_shell(dto_object)
            log.info(f"Успешно создана 'оболочка' персонажа с char_id={char_id} для user_id={self.user_id}.")
            return char_id
        except SQLAlchemyError as e:
            log.exception(f"Ошибка при создании 'оболочки' персонажа для user_id={self.user_id}: {e}")
            await session.rollback()
            raise

    async def get_data_characters(self, session: AsyncSession) -> list[CharacterReadDTO] | None:
        try:
            char_repo = get_character_repo(session)
            character = await char_repo.get_characters(self.user_id)
            if character:
                return character
            else:
                return None
        except SQLAlchemyError as e:
            log.exception(f"Ошибка при получении списка персонажей для user_id={self.user_id}: {e}")
            return None

    async def delete_character_ind_db(self, session: AsyncSession) -> bool:
        if not self.char_id:
            return False
        try:
            char_repo = get_character_repo(session)
            await char_repo.delete_characters(self.char_id)
            return True

        except SQLAlchemyError as e:
            log.exception(f"Ошибка при удалении персонажа {self.char_id} ошибка {e}")
            return False

    async def get_fsm_data(self, characters_dto: list[CharacterReadDTO]) -> dict[str, Any]:
        """Собирает данные сервиса для сохранения в FSM"""
        characters = await fsm_store(characters_dto)
        return {"char_id": self.char_id, "characters": characters, "user_id": self.user_id}
