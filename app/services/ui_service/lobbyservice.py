from typing import Optional, List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, User
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.schemas_dto.character_dto import CharacterReadDTO, CharacterOnboardingUpdateDTO
from app.resources.texts.buttons_callback import Buttons
from app.services.helpers_module.DTO_helper import fsm_store
from app.services.ui_service.helpers_ui.lobby_formatters import LobbyFormatter
from app.resources.schemas_dto.character_dto import CharacterShellCreateDTO
from database.repositories import get_character_repo
from database.session import get_async_session


class LobbyService:
    """
    Сервис для управления логикой лобби выбора персонажей.

    Этот класс инкапсулирует операции, связанные с отображением списка
    персонажей, созданием клавиатур и взаимодействием с базой данных
    для создания и обновления персонажей.
    """

    def __init__(
            self,
            user: User,
            selected_char_id: Optional[int] = None,
            characters: Optional[List[CharacterReadDTO]] = None,
    ):
        """
        Инициализирует сервис лобби.

        Args:
            user (User): Объект пользователя Telegram.
            selected_char_id (Optional[int], optional): ID текущего выбранного
                персонажа для подсветки в клавиатуре. Defaults to None.
            characters (Optional[List[CharacterReadDTO]], optional): Список
                персонажей пользователя. Defaults to None.
        """
        self.buttons = Buttons
        self.characters = characters if characters is not None else []
        self.selected_char_id = selected_char_id
        self.user_id = user.id

    async def get_data_lobby_start(self) -> tuple[str, InlineKeyboardMarkup]:
        """
        Подготавливает данные для отображения стартового экрана лобби.

        Форматирует текст со списком персонажей и создает соответствующую
        клавиатуру.

        Returns:
            tuple[str, InlineKeyboardMarkup]: Кортеж, содержащий текст
            сообщения и клавиатуру.
        """
        text = LobbyFormatter.format_character_list(self.characters)
        kb = await self._get_character_lobby_kb()
        return text, kb

    async def _get_character_lobby_kb(self, max_slots: int = 4) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру для лобби выбора персонажа.

        Генерирует кнопки для каждого персонажа и кнопки действий
        ("Создать", "Войти в игру", "Выйти").

        Args:
            max_slots (int, optional): Максимальное количество слотов для
                персонажей. Defaults to 4.

        Returns:
            InlineKeyboardMarkup: Готовая клавиатура для лобби.
        """
        kb = InlineKeyboardBuilder()
        lobby_data = Buttons.LOBBY

        characters = await fsm_store(self.characters)

        # === Блок персонажей (2x2) ===
        # Создаем кнопки для существующих персонажей и пустые слоты.
        for i in range(max_slots):
            if i < len(characters):
                char = characters[i]
                char_id = char.get('character_id')
                # Добавляем эмодзи для визуального выделения выбранного персонажа.
                is_selected = char_id == self.selected_char_id
                prefix = '✅ ' if is_selected else '👤 '
                kb.button(
                    text=f"{prefix}{char.get('name')}",
                    callback_data=f"lobby:select:{char_id}"
                )
            else:
                # Если слот пуст, добавляем кнопку создания нового персонажа.
                kb.button(text=lobby_data["lobby:create"], callback_data="lobby:create")
        kb.adjust(2, 2)

        # === Блок действий (по одной на строку) ===
        actions = ["logout", "lobby:login"]
        for cb in actions:
            kb.row(InlineKeyboardButton(text=lobby_data[cb], callback_data=cb))

        return kb.as_markup()

    async def create_und_get_character_id(self) -> int:
        """
        Создает "оболочку" персонажа в базе данных и возвращает его ID.

        "Оболочка" - это минимальная запись в БД, которая создается до того,
        как пользователь введет имя и выберет пол.

        Returns:
            int: ID созданного персонажа.
        """
        dto_object = CharacterShellCreateDTO(user_id=self.user_id)
        async with get_async_session() as session:
            char_repo = get_character_repo(session)
            char_id = await char_repo.create_character_shell(dto_object)
        return char_id

    async def update_character_db(self, char_update_dto: CharacterOnboardingUpdateDTO):
        """
        Обновляет данные персонажа на этапе создания (onboarding).

        Args:
            char_update_dto (CharacterOnboardingUpdateDTO): DTO с данными
                для обновления (имя, пол и т.д.).

        Returns:
            None
        """
        async with get_async_session() as session:
            char_repo = get_character_repo(session)
            await char_repo.update_character_onboarding(
                character_id=self.selected_char_id,
                character_data=char_update_dto
            )
