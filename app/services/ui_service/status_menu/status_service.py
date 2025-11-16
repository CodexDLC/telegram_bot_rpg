from loguru import logger as log
from typing import Tuple, Optional, Dict, Any, Type

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.game_data.status_menu.bio_group_data import TABS_NAV_DATA, BIO_HIERARCHY
from app.resources.game_data.status_menu.modifer_group_data import MODIFIER_HIERARCHY
from app.resources.game_data.status_menu.skill_group_data import SKILL_HIERARCHY
from app.resources.keyboards.status_callback import (
    StatusNavCallback,
    StatusSkillsCallback,
    StatusModifierCallback
)
from app.services.ui_service.base_service import BaseUIService
from app.services.ui_service.helpers_ui.skill_formatters import SkillFormatters as SkillF

from app.resources.schemas_dto.character_dto import CharacterReadDTO
from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from app.services.ui_service.helpers_ui.status_formatters import StatusFormatter as StatusF
from app.services.ui_service.helpers_ui.status_modiier_formatters import ModifierFormatters as ModifierF
from database.repositories import get_character_repo
from database.session import get_async_session


class CharacterMenuUIService(BaseUIService):
    """
    Сервис для формирования UI-компонентов меню статуса персонажа.

    Отвечает за создание текста и навигационной клавиатуры для различных
    вкладок меню статуса, таких как "Биография", "Навыки" и т.д.
    """

    def __init__(
            self,
            char_id: int,
            callback_data: StatusNavCallback,
            state_data: dict[str, Any],
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
        super().__init__(char_id=char_id, state_data=state_data)

        self.actor_name = syb_name or DEFAULT_ACTOR_NAME
        self.status_buttons = TABS_NAV_DATA
        self.data_bio = BIO_HIERARCHY.get("bio", {})
        self.data_skill = SKILL_HIERARCHY
        self.data_mod = MODIFIER_HIERARCHY
        self.call_type = callback_data.key

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
        text_formated = self.data_bio.get("description", "Нет данных.").format(
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

    def status_message_skill_message(
            self,
            character: CharacterReadDTO
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Возвращает текст и клавиатуру для отображения групп навыков.

        Returns:
            Tuple[str, InlineKeyboardMarkup]: Текст и клавиатура.
        """
        log.debug(f"Подготовка сообщения со списком групп навыков для char_id={self.char_id}.")
        if character is None:
            log.warning(f"Данные персонажа (character) отсутствуют для char_id={self.char_id}.")
            return "Ошибка: данные персонажа не найдены.", InlineKeyboardBuilder().as_markup()

        data_skills = self.data_skill.get("skills")
        data = data_skills.get("items")

        char_name = character.name
        syb_name = self.actor_name

        text = SkillF.group_skill(data=data, char_name=char_name, actor_name=syb_name)
        kb = self._build_group_kb(items=data, callback_factory=StatusSkillsCallback)
        return text, kb

    def status_message_modifier_message(
            self,
            character: CharacterReadDTO
    ) -> Tuple[str, InlineKeyboardMarkup]:

        data = self.data_mod.get("stats", {}).get("items", {})

        char_name = character.name
        syb_name = self.actor_name
        text = ModifierF.group_modifier(data, char_name, syb_name)
        kb = self._build_group_kb(items=data, callback_factory=StatusModifierCallback)

        return text, kb

    # =================================================================
    # МЕТОДЫ ГЕНЕРАЦИИ КЛАВИАТУР
    # =================================================================

    def _status_kb(self) -> InlineKeyboardMarkup:
        """
        Создает БАЗОВУЮ навигационную клавиатуру (только нижний ряд).
        Используется там, где нет кнопок групп (например, "Био").
        """
        kb = InlineKeyboardBuilder()
        log.debug(f"Создание базовой навигационной клавиатуры. Активная вкладка: '{self.call_type}'.")

        buttons_to_add = self._status_buttons()
        if buttons_to_add:
            kb.row(*buttons_to_add)
            log.debug(f"Добавлено {len(buttons_to_add)} навигационных кнопок.")

        return kb.as_markup()

    def _build_group_kb(
            self,
            items: Dict[str, str],
            callback_factory: Type[CallbackData]
    ) -> InlineKeyboardMarkup:
        """
        УНИВЕРСАЛЬНЫЙ метод. Строит клавиатуру с группами (Навыки, Статы).

        Он делает ВСЁ:
        1. Строит сетку кнопок групп (Навыки или Статы).
        2. Добавляет нижний ряд навигации.
        """
        kb = InlineKeyboardBuilder()
        log.debug(f"Создание универсальной клавиатуры групп для '{callback_factory.__name__}'.")

        # --- 1. Строим сетку кнопок (Навыки, Статы и т.д.) ---
        if items:
            for key, value in items.items():
                callback_data = callback_factory(
                    char_id=self.char_id,
                    level="group",
                    key=key
                ).pack()
                kb.button(text=value, callback_data=callback_data)
            kb.adjust(2)
            log.debug(f"Построена сетка из {len(items)} элементов.")
        else:
            log.warning(f"Нет 'items' для построения сетки кнопок (char_id={self.char_id}).")

        # --- 2. Добавляем нижний ряд навигации ---
        buttons_to_add = self._status_buttons()
        if buttons_to_add:
            kb.row(*buttons_to_add)
            log.debug(f"Добавлен навигационный ряд из {len(buttons_to_add)} кнопок.")

        return kb.as_markup()

    def _status_buttons(self):
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

        return buttons_to_add

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