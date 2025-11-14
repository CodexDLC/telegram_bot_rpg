# app/services/ui_service/character_skill_service.py
import logging
from typing import Any, Optional, List, Dict, Tuple

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME

from app.services.ui_service.helpers_ui.skill_formatters import SkillFormatters as SkillF

log = logging.getLogger(__name__)


class CharacterSkillStatusService:
    """
    Сервис для управления UI-логикой меню навыков персонажа.

    Формирует текст и клавиатуры для различных уровней вложенности:
    от общего списка групп до детальной информации о конкретном навыке.
    """

    def __init__(self,
                 char_id: int,
                 call_type: str,
                 view_mode: str,
                 character: Dict[str, Any],
                 character_skill: List[Dict[str, Any]]
                 ):
        """
        Инициализирует сервис меню навыков.

        Args:
            char_id (int): ID персонажа.
            call_type (str): Тип текущего действия (e.g., "skills").
            view_mode (str): Режим просмотра (e.g., "lobby").
            character (Dict[str, Any]): Словарь с данными о персонаже.
            character_skill (List[Dict[str, Any]]): Список словарей с прогрессом навыков.
        """
        self.char_id = char_id
        self.character = character
        self.call_type = call_type
        self.view_mode = view_mode
        self.actor_name = DEFAULT_ACTOR_NAME
        self.data_skill = SKILL_UI_GROUPS_MAP
        self.b_status = STATUS_ACTION
        self.character_skill = character_skill
        log.debug(f"Инициализирован {self.__class__.__name__} для char_id={char_id}, view_mode='{view_mode}'.")

    def data_message_all_group_skill(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Возвращает текст и клавиатуру для отображения групп навыков.

        Returns:
            Tuple[str, InlineKeyboardMarkup]: Текст и клавиатура.
        """
        log.debug(f"Подготовка сообщения со списком групп навыков для char_id={self.char_id}.")
        if self.character is None:
            log.warning(f"Данные персонажа (character) отсутствуют для char_id={self.char_id}.")
            return "Ошибка: данные персонажа не найдены.", InlineKeyboardBuilder().as_markup()

        char_name = self.character.get('name')
        syb_name = DEFAULT_ACTOR_NAME if self.view_mode == "lobby" else self.actor_name
        text = SkillF.group_skill(self.data_skill, char_name, syb_name)
        kb = self._start_skill_kb()
        return text, kb

    def data_message_group_skill(self, group_type: Optional[str]) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Возвращает текст и клавиатуру для навыков в конкретной группе.

        Args:
            group_type (Optional[str]): Ключ группы навыков (e.g., "combat").

        Returns:
            Tuple[str, InlineKeyboardMarkup]: Текст и клавиатура.
        """
        log.debug(f"Подготовка сообщения со списком навыков группы '{group_type}' для char_id={self.char_id}.")
        char_name = self.character.get('name')
        syb_name = DEFAULT_ACTOR_NAME if self.view_mode == "lobby" else self.actor_name
        text = SkillF.format_skill_list_in_group(
            data=self.data_skill,
            group_type=group_type,
            char_name=char_name,
            actor_name=syb_name,
            view_mode=self.view_mode,
            character_skill=self.character_skill
        )
        kb = self._group_skill_kb(group_type=group_type)
        return text, kb

    def _group_skill_kb(self, group_type: Optional[str]) -> InlineKeyboardMarkup:
        """Создает клавиатуру для списка навыков в группе."""
        kb = InlineKeyboardBuilder()
        log.debug(f"Создание клавиатуры для группы '{group_type}'.")

        if self.view_mode != "lobby":
            skill_dict = self.data_skill.get(group_type, {}).get('skills', {})
            for key, value in skill_dict.items():
                kb.button(
                    text=value,
                    callback_data=SkillMenuCallback(level="detail", value=key, char_id=self.char_id, view_mode=self.view_mode).pack()
                )
            kb.adjust(2)
            log.debug(f"Добавлено {len(skill_dict)} кнопок навыков.")

        back_callback = StatusMenuCallback(action="skills", char_id=self.char_id, view_mode=self.view_mode).pack()
        kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data=back_callback))
        return kb.as_markup()

    def _start_skill_kb(self) -> InlineKeyboardMarkup:
        """Создает клавиатуру для верхнего уровня меню навыков (список групп)."""
        kb = InlineKeyboardBuilder()
        log.debug("Создание клавиатуры для списка групп навыков.")

        for group, value in self.data_skill.items():
            text = value.get("title_ru")
            kb.button(
                text=text,
                callback_data=SkillMenuCallback(level="group", value=group, char_id=self.char_id, view_mode=self.view_mode).pack(),
            )
        kb.adjust(2)
        log.debug(f"Добавлено {len(self.data_skill)} кнопок групп.")

        self._create_navigation_buttons(kb)
        return kb.as_markup()

    def _create_navigation_buttons(self, kb: InlineKeyboardBuilder) -> None:
        """Добавляет стандартные навигационные кнопки в меню статуса."""
        log.debug("Добавление навигационных кнопок в клавиатуру.")
        active_callback_action = self.call_type
        buttons_to_add = []

        for key, value in self.b_status.items():
            if key == active_callback_action:
                continue  # Не добавляем кнопку для уже активной вкладки.

            if key == "nav:start" and self.view_mode == "lobby":
                continue  # Не добавляем "Закрыть" в режиме лобби.

            callback_data = StatusMenuCallback(action=key, char_id=self.char_id, view_mode=self.view_mode).pack()
            buttons_to_add.append(InlineKeyboardButton(text=value, callback_data=callback_data))

        if buttons_to_add:
            kb.row(*buttons_to_add)
            log.debug(f"Добавлено {len(buttons_to_add)} навигационных кнопок.")
