# app/services/ui_service/lobbyservice.py
import logging
from typing import Optional, List, Tuple, Dict, Any

from aiogram.types import InlineKeyboardMarkup, User, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.schemas_dto.character_dto import CharacterReadDTO, CharacterShellCreateDTO
from app.resources.texts.buttons_callback import Buttons
from app.services.helpers_module.DTO_helper import fsm_store
from app.services.ui_service.helpers_ui.lobby_formatters import LobbyFormatter
from database.repositories.ORM.characters_repo_orm import CharactersRepoORM
from database.session import get_async_session

# --- ИЗМЕНЕНИЕ: Импортируем оба колбэка ---
from app.resources.keyboards.callback_data import LobbySelectionCallback, StatusNavCallback

log = logging.getLogger(__name__)


class LobbyService:
    """
    Сервис для управления UI-логикой лобби выбора персонажей.
    """

    def __init__(
            self,
            user: User,
            char_id: int = None,
            characters: Optional[List[CharacterReadDTO]] = None,
    ):
        self.user_id = user.id
        self.characters = characters if characters is not None else []
        self.char_id = char_id if char_id is not None else None
        log.debug(
            f"Инициализирован {self.__class__.__name__} для user_id={self.user_id} с {len(self.characters)} персонажами.")

    def get_data_lobby_start(self) -> Tuple[str, InlineKeyboardMarkup]:
        log.debug(f"Подготовка стартового экрана лобби для user_id={self.user_id}.")
        text = LobbyFormatter.format_character_list(self.characters)
        kb = self._get_character_lobby_kb()
        return text, kb

    def _get_character_lobby_kb(self, max_slots: int = 4) -> InlineKeyboardMarkup:
        log.debug(f"Создание клавиатуры лобби для user_id={self.user_id}.")
        kb = InlineKeyboardBuilder()
        lobby_buttons = Buttons.LOBBY_KB_UP

        # Создаем кнопки для существующих персонажей.
        for i in range(max_slots):
            if i < len(self.characters):
                char = self.characters[i]

                # --- ИЗМЕНЕНИЕ ЗДЕСЬ ---
                # Кнопка выбора персонажа ("👤 Имя") теперь использует StatusNavCallback
                # и ведет в тот же хэндлер, что и кнопка "Статус"
                callback = StatusNavCallback(
                    key="bio",
                    char_id=char.character_id
                )

                text = f"✅ {char.name}" if char.character_id == self.char_id else f"👤 {char.name}"
                kb.button(text=text, callback_data=callback.pack())
            else:
                # --- БЕЗ ИЗМЕНЕНИЙ ---
                # Кнопка "Создать" по-прежнему использует LobbySelectionCallback
                callback = LobbySelectionCallback(
                    action="create",
                )
                kb.button(text=lobby_buttons["create"], callback_data=callback.pack())
        kb.adjust(2, 2)

        # Кнопки "Войти", "Удалить" (в _down_button) также используют LobbySelectionCallback
        buttons = self._down_button()
        for button in buttons:
            kb.row(button)

        log.debug("Клавиатура лобби успешно создана.")
        return kb.as_markup()

    def _down_button(self):
        # --- БЕЗ ИЗМЕНЕНИЙ ---
        # Эти кнопки (Войти, Удалить) по-прежнему используют LobbySelectionCallback
        lobby_buttons_dawn = Buttons.LOBBY_KB_DOWN
        buttons = []

        for key, value in lobby_buttons_dawn.items():
            buttons.append(InlineKeyboardButton(
                text=value,
                callback_data=LobbySelectionCallback(action=key).pack()
            ))

        return buttons

    async def create_und_get_character_id(self) -> int:
        # (Метод без изменений)
        log.info(f"Запрос на создание 'оболочки' персонажа для user_id={self.user_id}.")
        dto_object = CharacterShellCreateDTO(user_id=self.user_id)
        async with get_async_session() as session:
            char_repo = CharactersRepoORM(session)
            try:
                char_id = await char_repo.create_character_shell(dto_object)
                log.info(f"Успешно создана 'оболочка' персонажа с char_id={char_id} для user_id={self.user_id}.")
                return char_id
            except Exception as e:
                log.exception(f"Ошибка при создании 'оболочки' персонажа для user_id={self.user_id}: {e}")
                await session.rollback()
                raise

    async def get_fsm_data(self) -> Dict[str, Any]:
        # (Метод без изменений)
        characters = await fsm_store(self.characters)
        return {
            "char_id": self.char_id,
            "characters": characters,
            "user_id": self.user_id
        }