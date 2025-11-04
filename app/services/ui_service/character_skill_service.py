#app/services/ui_service/character_skill_service.py
import logging
from typing import Any, Optional

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.game_data.skill_library import SKILL_UI_GROUPS_MAP
from app.resources.keyboards.callback_data import StatusMenuCallback, SkillMenuCallback
from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from app.resources.texts.ui_text.data_text_status_menu import STATUS_ACTION
from app.services.ui_service.helpers_ui.skill_formatters import SkillFormatters as SkillF

log = logging.getLogger(__name__)

class CharacterSkillStatusService:

    def __init__(self,
                 char_id : int,
                 call_type: str,
                 view_mode: str,
                 character: dict[str, Any],
                 character_skill: list[dict[str, Any]]
                 ):

        self.char_id = char_id
        self.character = character
        self.call_type = call_type
        self.view_mode=view_mode
        self.actor_name = DEFAULT_ACTOR_NAME
        self.data_skill = SKILL_UI_GROUPS_MAP
        self.b_status = STATUS_ACTION
        self.character_skill = character_skill



    def data_message_all_group_skill(self):
        """
        :return: текст и клавиатуру с группами навыков
        """
        if self.character is None:
            log.warning(f"Character = {self.character}")

        char_name = self.character.get('name')
        syb_name = DEFAULT_ACTOR_NAME if self.call_type == "lobby" else self.actor_name
        text = SkillF.group_skill(self.data_skill, char_name, syb_name)
        kb = self._start_skill_kb()

        return text, kb

    def data_message_group_skill(self, group_type: Optional[str]):
        """
         текст и клавиатура для навыков в группе
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


    def data_message_skill(self, skill_type: Optional[str]):
        """
       text и клавиатура для показа подробных данных навыка
        """


        text = ""

        kb= ""

        return text, kb


    def _group_skill_kb(self, group_type: Optional[str]):
        """

        """
        kb = InlineKeyboardBuilder()

        if not self.data_skill:
            return None

        if self.view_mode != "lobby":
            skill_dict = self.data_skill[group_type]['skills']

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

        buttons = []
        back_callback = StatusMenuCallback(
            action="skills",
            char_id=self.char_id,
            view_mode=self.view_mode
        ).pack()

        buttons.append(InlineKeyboardButton(text="🔙 Назад", callback_data=back_callback))

        if buttons:
            kb.row(*buttons)

        return kb.as_markup()

    def _start_skill_kb(self):
        """
        :return: клавиатуру для первого режима
        """
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
        self._create_buttons(kb)
        return kb.as_markup()


    def _create_buttons(self, kb:InlineKeyboardBuilder):

        active_callback_action = self.call_type
        buttons = []
        for key, value in self.b_status.items():

            # Получаем 'bio' или 'skills'
            action = key

            if action == active_callback_action:
                continue

            # VVV Логика для кнопки "Закрыть" VVV
            if key == "nav:start":
                # Если мы в лобби, кнопка "Закрыть" не нужна
                if self.view_mode == "lobby":
                    continue
                # Это обычная кнопка, она не часть Фабрики
                b1 = InlineKeyboardButton(text=value, callback_data=key)
                buttons.append(b1)
                continue

            # Собираем callback через нашу Фабрику
            callback_data_str = StatusMenuCallback(
                action=action,
                char_id=self.char_id,
                view_mode=self.view_mode
            ).pack()

            b1 = InlineKeyboardButton(text=value, callback_data=callback_data_str)
            buttons.append(b1)

        if buttons:
            kb.row(*buttons)