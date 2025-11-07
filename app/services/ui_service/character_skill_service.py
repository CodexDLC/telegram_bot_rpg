# app/services/ui_service/character_skill_service.py
import logging
from typing import Any, Optional, List, Dict

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.game_data.skill_library import SKILL_UI_GROUPS_MAP
from app.resources.keyboards.callback_data import StatusMenuCallback, SkillMenuCallback
from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from app.resources.texts.ui_text.data_text_status_menu import STATUS_ACTION
from app.services.ui_service.helpers_ui.skill_formatters import SkillFormatters as SkillF

log = logging.getLogger(__name__)


class CharacterSkillStatusService:
    """
    Сервис для управления отображением меню навыков персонажа.

    Этот класс отвечает за формирование текста и клавиатур для различных
    уровней вложенности в меню навыков: от общего списка групп до
    детальной информации о конкретном навыке.
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
            view_mode (str): Режим просмотра (e.g., "lobby", "ingame").
            character (Dict[str, Any]): Словарь с данными о персонаже.
            character_skill (List[Dict[str, Any]]): Список словарей с данными
                о навыках персонажа.
        """
        self.char_id = char_id
        self.character = character
        self.call_type = call_type
        self.view_mode = view_mode
        self.actor_name = DEFAULT_ACTOR_NAME
        self.data_skill = SKILL_UI_GROUPS_MAP
        self.b_status = STATUS_ACTION
        self.character_skill = character_skill

    def data_message_all_group_skill(self) -> tuple[str, InlineKeyboardMarkup]:
        """
        Возвращает текст и клавиатуру для отображения групп навыков.

        Это верхний уровень меню навыков.

        Returns:
            tuple[str, InlineKeyboardMarkup]: Текст и клавиатура.
        """
        if self.character is None:
            log.warning(f"Данные персонажа отсутствуют (character is None).")
            # Возвращаем пустые значения, чтобы избежать падения.
            return "Ошибка: данные персонажа не найдены.", InlineKeyboardBuilder().as_markup()

        char_name = self.character.get('name')
        # Имя "рассказчика" зависит от контекста (лобби или игра).
        syb_name = DEFAULT_ACTOR_NAME if self.call_type == "lobby" else self.actor_name
        text = SkillF.group_skill(self.data_skill, char_name, syb_name)
        kb = self._start_skill_kb()

        return text, kb

    def data_message_group_skill(self, group_type: Optional[str]) -> tuple[str, InlineKeyboardMarkup]:
        """
        Возвращает текст и клавиатуру для навыков в конкретной группе.

        Args:
            group_type (Optional[str]): Ключ группы навыков (e.g., "combat").

        Returns:
            tuple[str, InlineKeyboardMarkup]: Текст и клавиатура.
        """
        char_name = self.character.get('name')
        syb_name = DEFAULT_ACTOR_NAME if self.call_type == "lobby" else self.actor_name
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

    def data_message_skill(self, skill_type: Optional[str]) -> tuple[str, str]:
        """
        Возвращает текст и клавиатуру для детального отображения навыка (заглушка).

        Args:
            skill_type (Optional[str]): Ключ конкретного навыка.

        Returns:
            tuple[str, str]: Текст и клавиатура.
        """
        text = ""
        kb = ""
        return text, kb

    def _group_skill_kb(self, group_type: Optional[str]) -> InlineKeyboardMarkup:
        """Создает клавиатуру для списка навыков в группе."""
        kb = InlineKeyboardBuilder()

        if not self.data_skill:
            return kb.as_markup()

        # Кнопки с навыками добавляются только если мы не в режиме "лобби".
        # В режиме лобби показывается только текстовый список.
        if self.view_mode != "lobby":
            skill_dict = self.data_skill.get(group_type, {}).get('skills', {})
            for key, value in skill_dict.items():
                kb.button(
                    text=value,
                    callback_data=SkillMenuCallback(
                        level="detail",
                        value=key,
                        char_id=self.char_id,
                        view_mode=self.view_mode
                    ).pack()
                )
            kb.adjust(2)

        # Добавляем кнопку "Назад" для возврата к списку групп.
        back_callback = StatusMenuCallback(
            action="skills",
            char_id=self.char_id,
            view_mode=self.view_mode
        ).pack()
        kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data=back_callback))

        return kb.as_markup()

    def _start_skill_kb(self) -> InlineKeyboardMarkup:
        """Создает клавиатуру для верхнего уровня меню навыков (список групп)."""
        kb = InlineKeyboardBuilder()

        for group, value in self.data_skill.items():
            text = value.get("title_ru")
            kb.button(
                text=text,
                callback_data=SkillMenuCallback(
                    level="group",
                    value=group,
                    char_id=self.char_id,
                    view_mode=self.view_mode,
                ).pack(),
            )
        kb.adjust(2)
        # Добавляем общие навигационные кнопки (Назад, Биография и т.д.).
        self._create_navigation_buttons(kb)
        return kb.as_markup()

    def _create_navigation_buttons(self, kb: InlineKeyboardBuilder):
        """Добавляет стандартные навигационные кнопки в меню статуса."""
        active_callback_action = self.call_type
        buttons = []
        for key, value in self.b_status.items():
            action = key
            # Не добавляем кнопку для уже активной вкладки.
            if action == active_callback_action:
                continue

            # Кнопка "Закрыть" обрабатывается особо, т.к. она не в режиме лобби.
            if key == "nav:start":
                if self.view_mode == "lobby":
                    continue
                buttons.append(InlineKeyboardButton(text=value, callback_data=key))
                continue

            # Собираем callback через фабрику для остальных кнопок.
            callback_data_str = StatusMenuCallback(
                action=action,
                char_id=self.char_id,
                view_mode=self.view_mode
            ).pack()
            buttons.append(InlineKeyboardButton(text=value, callback_data=callback_data_str))

        if buttons:
            kb.row(*buttons)
