# app/services/ui_service/status_skill_service.py
import logging
from typing import Any, Optional, Dict, Tuple

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.game_data.status_menu.skill_group_data import SKILL_HIERARCHY
from app.resources.keyboards.status_callback import StatusSkillsCallback, StatusNavCallback
from app.resources.schemas_dto.skill import SkillProgressDTO, SkillDisplayDTO
from app.services.ui_service.helpers_ui.skill_formatters import SkillFormatters as SkillF
from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from app.services.ui_service.base_service import BaseUIService
from database.repositories import get_skill_rate_repo, get_skill_progress_repo

from database.repositories.ORM.skill_repo import SkillProgressRepo
from database.session import get_async_session

log = logging.getLogger(__name__)


class CharacterSkillStatusService(BaseUIService):
    """
    Сервис для управления UI-логикой меню навыков персонажа.

    Формирует текст и клавиатуры для различных уровней вложенности:
    от общего списка групп до детальной информации о конкретном навыке.
    """

    def __init__(self,
                 char_id: int,
                 key: str,
                 state_data: Dict[str, Any],
                 syb_name: Optional[str] = None,
                 ):
        """

        """
        super().__init__(char_id=char_id, state_data=state_data)
        self.char_id = char_id
        if syb_name is None:
            self.actor_name = DEFAULT_ACTOR_NAME
        else:
            self.actor_name = syb_name
        self.data_skills = SKILL_HIERARCHY
        self.data_group = self.data_skills.get(key)
        self.state_data = state_data
        log.debug(f"Инициализирован {self.__class__.__name__} для char_id={char_id}.")



    def status_group_skill_message(
            self,
            character_skills: list[SkillProgressDTO]
    ) -> Tuple[str, InlineKeyboardMarkup]:

        sor_list_dto = self._sorted_group_skill(
            character_skills=character_skills,
            group_item=self.data_group.get("items")
        )

        text = SkillF.format_skill_list_in_group(
            char_id = self.char_id,
            data_group = self.data_group,
            data_skill = sor_list_dto,
            actor_name=self.actor_name
        )


        kb = self._group_skill_kb(sor_list_dto)

        return text , kb



    def _group_skill_kb(self, sor_list_dto: list[SkillProgressDTO]) -> InlineKeyboardMarkup:
        """Создает клавиатуру для списка навыков в группе."""
        kb = InlineKeyboardBuilder()

        data_items = self.data_group.get("items")

        for skill in sor_list_dto:
            callback_data = StatusSkillsCallback(
                    char_id=self.char_id,
                    level="detail",
                    key=skill.skill_key
                ).pack()
            kb.button(text=data_items.get(skill.skill_key), callback_data=callback_data)
        kb.adjust(2)

        back_callback = StatusNavCallback(
            char_id=self.char_id,
            key="skills"  # Ключ Lvl 0, который показывает Lvl 1 (список групп)
        ).pack()

        # Мы добавляем ее отдельным рядом .row()
        kb.row(
            InlineKeyboardButton(text="[ ◀️ Назад к группам ]", callback_data=back_callback)
        )
        return kb.as_markup()

    def _sorted_group_skill(
            self,
            character_skills: list[SkillProgressDTO],
            group_item: dict[str, str]
    ) -> list[SkillProgressDTO]:

        data_group_items = self.data_group.get("items")
        view_data = []

        if group_item:
            for skill in character_skills:
                if skill.skill_key in data_group_items and skill.is_unlocked == True:
                    view_data.append(skill)


        return view_data


    async def get_list_skills_dto(self):

        try:
            async with get_async_session() as session:
                skill_progress = get_skill_progress_repo(session)
                skills_data = skill_progress.get_all_skills_progress(character_id=self.char_id)
                if skills_data:
                    log.debug(f"")
                    return skills_data
                else:
                    log.warning(f"")
                    return None

        except Exception as e:
            log.error(f"Ошибка при получении данных для char_id={self.char_id}: {e}", exc_info=True)
            raise


