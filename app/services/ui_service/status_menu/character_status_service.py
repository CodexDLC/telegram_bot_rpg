# app/services/ui_service/status_menu/character_status_service.py
import logging
from typing import Tuple, Optional, Dict, Any

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.game_data.status_menu.bio_group_data import TABS_NAV_DATA, BIO_HIERARCHY
from app.resources.keyboards.callback_data import StatusNavCallback
from app.resources.schemas_dto.character_dto import CharacterReadDTO
from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from app.services.ui_service.helpers_ui.status_formatters import StatusFormatter as StatusF
from database.repositories import get_character_repo
from database.session import get_async_session

log = logging.getLogger(__name__)


class CharacterMenuUIService:
    """
    Сервис для формирования UI-компонентов меню статуса персонажа.

    Отвечает за создание текста и навигационной клавиатуры для различных
    вкладок меню статуса, таких как "Биография", "Навыки" и т.д.
    """

    def __init__(
            self,
            char_id: int,
            callback_data: StatusNavCallback,
            state_data: Dict[str, Any],
            syb_name: Optional[str] = None,
    ):
        """
        Инициализирует сервис для меню статуса персонажа.

        Args:
            char_id: Уникальный идентификатор персонажа.
            callback_data: Данные из callback-кнопки, определяющие текущую вкладку.
            state_data: Данные из FSM-состояния.
            syb_name: Имя "рассказчика" (актора), от лица которого
                      отображается информация. Если None, используется
                      значение по умолчанию.
        """
        self.char_id = char_id
        self.actor_name = syb_name or DEFAULT_ACTOR_NAME
        self.status_buttons = TABS_NAV_DATA
        self.data_lib = BIO_HIERARCHY.get("bio", {})
        self.call_type = callback_data.key
        self.state_data = state_data

        log.debug(
            f"Initialized {self.__class__.__name__} for char_id={char_id}, "
            f"call_type='{self.call_type}', actor='{self.actor_name}'"
        )

    def staus_bio_message(
            self,
            character: CharacterReadDTO,
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Формирует текст и клавиатуру для вкладки "Биография".

        Args:
            character: DTO с данными персонажа.

        Returns:
            Кортеж, содержащий отформатированный текст и
            навигационную клавиатуру.
        """
        log.debug(f"Формирование сообщения 'Биография' для char_id={self.char_id}.")

        # Форматируем основной текст биографии
        text_formated = self.data_lib.get("description", "Нет данных.").format(
            name=character.name,
            gender=character.gender,
            created_at=character.created_at.strftime('%d-%m-%Y %H:%M'),
        )

        # Оборачиваем текст в стандартный шаблон сообщения от актора
        text = StatusF.format_character_bio(
            text_formated=text_formated,
            actor_name=self.actor_name
        )

        kb = self._status_kb()
        log.debug(f"Сообщение 'Биография' для char_id={self.char_id} успешно сформировано.")
        return text, kb

    def _status_kb(self) -> InlineKeyboardMarkup:
        """
        Создает навигационную клавиатуру для меню статуса.

        Содержит кнопки для переключения между вкладками. Кнопка для
        текущей активной вкладки не создается.

        Returns:
            Готовая навигационная клавиатура.
        """
        kb = InlineKeyboardBuilder()
        log.debug(f"Создание навигационной клавиатуры для меню статуса. Активная вкладка: '{self.call_type}'.")

        buttons_to_add = []
        for key, value in self.status_buttons.items():
            # Пропускаем создание кнопки для уже активной вкладки.
            if key == self.call_type:
                continue

            callback_data = StatusNavCallback(
                char_id=self.char_id,
                key=key,
            ).pack()
            buttons_to_add.append(InlineKeyboardButton(text=value, callback_data=callback_data))

        if buttons_to_add:
            kb.row(*buttons_to_add)
            log.debug(f"Добавлено {len(buttons_to_add)} навигационных кнопок.")

        return kb.as_markup()

    def get_message_data(self) -> Optional[Tuple[int, int]]:
        """
        Извлекает chat_id и message_id из данных состояния FSM.

        Returns:
            Кортеж (chat_id, message_id) в случае успеха, иначе None.
        """
        message_content = self.state_data.get("message_content")
        if not message_content:
            log.warning(f"В FSM state для char_id={self.char_id} отсутствует 'message_content'.")
            return None

        chat_id = message_content.get("chat_id")
        message_id = message_content.get("message_id")

        if not chat_id or not message_id:
            log.warning(
                f"В 'message_content' для char_id={self.char_id} отсутствует "
                f"'chat_id' или 'message_id'."
            )
            return None

        log.debug(f"Извлечены данные сообщения: chat_id={chat_id}, message_id={message_id}.")
        return chat_id, message_id

    async def get_data_service(self) -> Optional[CharacterReadDTO]:
        """
        Асинхронно получает данные персонажа из репозитория.

        Returns:
            DTO персонажа в случае успеха, иначе None.

        Raises:
            Exception: Пробрасывает исключения, возникшие при работе с БД.
        """
        log.debug(f"Запрос данных для персонажа с char_id={self.char_id} из БД.")
        try:
            async with get_async_session() as session:
                char_repo = get_character_repo(session)
                character = await char_repo.get_character(self.char_id)
                if character:
                    log.debug(f"Персонаж с char_id={self.char_id} успешно получен.")
                    return character
                else:
                    log.warning(f"Персонаж с char_id={self.char_id} не найден в БД.")
                    return None
        except Exception as e:
            log.error(f"Ошибка при получении данных для char_id={self.char_id}: {e}", exc_info=True)
            raise
