# app/services/ui_service/lobbyservice.py
import logging
from typing import Optional, List, Tuple

from aiogram.types import InlineKeyboardMarkup, User
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.schemas_dto.character_dto import CharacterReadDTO, CharacterOnboardingUpdateDTO, CharacterShellCreateDTO
from app.resources.texts.buttons_callback import Buttons
from app.services.ui_service.helpers_ui.lobby_formatters import LobbyFormatter
from database.repositories.ORM.characters_repo_orm import CharactersRepoORM
from database.session import get_async_session

log = logging.getLogger(__name__)


class LobbyService:
    """
    Сервис для управления UI-логикой лобби выбора персонажей.

    Инкапсулирует операции, связанные с отображением списка персонажей,
    созданием клавиатур и взаимодействием с БД для создания персонажей.
    """

    def __init__(
            self,
            user: User,
            characters: Optional[List[CharacterReadDTO]] = None,
    ):
        """
        Инициализирует сервис лобби.

        Args:
            user (User): Объект пользователя Telegram.
            characters (Optional[List[CharacterReadDTO]]): Список DTO персонажей.
        """
        self.user_id = user.id
        self.characters = characters if characters is not None else []
        log.debug(f"Инициализирован {self.__class__.__name__} для user_id={self.user_id} с {len(self.characters)} персонажами.")

    async def get_data_lobby_start(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Подготавливает данные для отображения стартового экрана лобби.

        Returns:
            Tuple[str, InlineKeyboardMarkup]: Кортеж с текстом и клавиатурой.
        """
        log.debug(f"Подготовка стартового экрана лобби для user_id={self.user_id}.")
        text = LobbyFormatter.format_character_list(self.characters)
        kb = self._get_character_lobby_kb()
        return text, kb

    def _get_character_lobby_kb(self, max_slots: int = 4) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру для лобби выбора персонажа.

        Args:
            max_slots (int): Максимальное количество слотов для персонажей.

        Returns:
            InlineKeyboardMarkup: Готовая клавиатура для лобби.
        """
        log.debug(f"Создание клавиатуры лобби для user_id={self.user_id}.")
        kb = InlineKeyboardBuilder()
        lobby_buttons = Buttons.LOBBY

        # Создаем кнопки для существующих персонажей.
        for i in range(max_slots):
            if i < len(self.characters):
                char = self.characters[i]
                kb.button(
                    text=f"👤 {char.name}",
                    callback_data=f"lobby:select:{char.character_id}"
                )
            else:
                # Если слот пуст, добавляем кнопку создания.
                kb.button(text=lobby_buttons["lobby:create"], callback_data="lobby:create")
        kb.adjust(2)  # По 2 кнопки в ряду для персонажей/создания.

        # Добавляем кнопки действий.
        kb.row(Buttons.get_button("lobby:login"))
        kb.row(Buttons.get_button("logout"))

        log.debug("Клавиатура лобби успешно создана.")
        return kb.as_markup()

    async def create_und_get_character_id(self) -> int:
        """
        Создает "оболочку" персонажа в БД и возвращает его ID.

        "Оболочка" - это минимальная запись, создаваемая до ввода имени/пола.
        Использует собственную сессию для выполнения этой изолированной операции.

        Returns:
            int: ID созданного персонажа.
        """
        log.info(f"Запрос на создание 'оболочки' персонажа для user_id={self.user_id}.")
        dto_object = CharacterShellCreateDTO(user_id=self.user_id)
        async with get_async_session() as session:
            char_repo = CharactersRepoORM(session)
            try:
                char_id = await char_repo.create_character_shell(dto_object)
                await session.commit() # Коммитим, так как сессия локальная
                log.info(f"Успешно создана 'оболочка' персонажа с char_id={char_id} для user_id={self.user_id}.")
                return char_id
            except Exception as e:
                log.exception(f"Ошибка при создании 'оболочки' персонажа для user_id={self.user_id}: {e}")
                await session.rollback()
                raise

    async def update_character_db(self, char_id: int, char_update_dto: CharacterOnboardingUpdateDTO) -> None:
        """
        Обновляет данные персонажа на этапе создания (onboarding).

        Использует собственную сессию для выполнения этой операции.

        Args:
            char_id (int): ID персонажа для обновления.
            char_update_dto (CharacterOnboardingUpdateDTO): DTO с данными.

        Returns:
            None
        """
        log.info(f"Запрос на обновление данных онбординга для char_id={char_id}.")
        log.debug(f"Данные для обновления: {char_update_dto.model_dump_json()}")
        async with get_async_session() as session:
            char_repo = CharactersRepoORM(session)
            try:
                await char_repo.update_character_onboarding(
                    character_id=char_id,
                    character_data=char_update_dto
                )
                await session.commit()
                log.info(f"Данные персонажа {char_id} успешно обновлены.")
            except Exception as e:
                log.exception(f"Ошибка при обновлении данных онбординга для char_id={char_id}: {e}")
                await session.rollback()
                raise
