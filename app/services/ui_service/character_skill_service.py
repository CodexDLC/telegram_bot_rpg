#app/services/ui_service/character_skill_service.py
import logging
from typing import Any, Optional

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.game_data.skill_library import SKILL_UI_GROUPS_MAP
from app.resources.texts.ui_text.data_text_status_menu import STATUS_ACTION
from app.services.ui_service.helpers_ui.skill_formatters import SkillFormatters as SkillF

log = logging.getLogger(__name__)

class CharacterSkillStatusServer:

    def __init__(self,
                 char_id : int,
                 state_fsm: str,
                 call_type: str,
                 character: dict[str, Any],
                 character_skill: list[dict[str, Any]]
                 ):

        self.char_id = char_id
        self.fsm_state = state_fsm
        self.character = character
        self.call_type = call_type
        self.data_skill = SKILL_UI_GROUPS_MAP
        self.b_status = STATUS_ACTION
        self.character_skill = character_skill


    def data_message_all_group_skill(self):
        """
        :return: текст и клавиатуру с группами навыков
        """
        char_name = self.character.get('name')
        text = SkillF.group_skill(self.data_skill, char_name)
        kb = self._start_skill_kb()

        return text, kb

    def data_message_group_skill(self, group_type: Optional[str]):
        """
         текст и клавиатура для навыков в группе
        """
        char_name = self.character.get('name')
        text = SkillF.format_skill_list_in_group(
            data=self.data_skill,
            group_type=group_type,
            char_name=char_name,
            character_skill=self.character_skill
        )

        kb = self._group_skill_kb()

        return text, kb


    def data_message_skill(self, skill_type: Optional[str]):
        """
       text и клавиатура для показа подробных данных навыка
        """


        text = ""

        kb= ""

        return text, kb


    def _group_skill_kb(self, group_type: Optional[str]):
        kb = InlineKeyboardBuilder()

        if not self.data_skill:
            return None

        skill_dict = self.data_skill[group_type]["skills"]
        for key, value in skill_dict:
            kb.button(text=value, callback_data=f"status:skills:group:skill:{key}")

        kb.adjust(2)

        buttons = []
        back_callback = f"status:skills:{self.char_id}"
        buttons.append(kb.button(text="🔙 Назад", callback_data=back_callback))

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
            kb.button(text=f"{text}", callback_data=f"status:skills:group:{group}")

        kb.adjust(3)

        self._create_buttons(kb)

        return kb.as_markup()


    def _create_buttons(self,kb: InlineKeyboardBuilder):

        active_callback = f"status:{self.call_type}"
        buttons = []
        for key, value in self.b_status.items():

            if key == active_callback:
                continue

            if key == "nav:start":
                # Если мы в лобби, кнопка "Закрыть" не нужна
                if self.fsm_state == "CharacterLobby.selection":
                    continue

            callback_data = f"{key}:{self.char_id}" if key.startswith("status:") else key

            b1 = InlineKeyboardButton(text=value, callback_data=callback_data)
            buttons.append(b1)

        if buttons:
            kb.row(*buttons)

