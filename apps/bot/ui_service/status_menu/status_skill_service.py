from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from apps.bot.resources.keyboards.status_callback import (
    SkillModeCallback,
    StatusNavCallback,
    StatusSkillsCallback,
)
from apps.bot.resources.status_menu.skill_group_data import SKILL_HIERARCHY
from apps.bot.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from apps.bot.ui_service.base_service import BaseUIService
from apps.bot.ui_service.status_menu.formatters.skill_formatters import (
    SkillFormatters as SkillF,
)
from apps.common.database.model_orm.skill import SkillProgressState
from apps.common.schemas_dto import SkillProgressDTO
from apps.common.schemas_dto.status_dto import FullCharacterDataDTO
from apps.game_core.game_service.skill.calculator_service import (
    SkillCalculatorService as SkillCal,
)


class CharacterSkillStatusService(BaseUIService):
    """
    Сервис для управления UI-логикой меню навыков персонажа.
    """

    def __init__(
        self,
        callback_data: StatusNavCallback | StatusSkillsCallback,
        state_data: dict[str, Any],
        symbiotic_name: str | None = None,
    ):
        super().__init__(char_id=callback_data.char_id, state_data=state_data)
        self.actor_name = symbiotic_name or DEFAULT_ACTOR_NAME
        self.data_skills = SKILL_HIERARCHY
        self.key = callback_data.key

        # Определяем уровень вложенности
        if isinstance(callback_data, StatusSkillsCallback):
            self.level = callback_data.level
        else:
            self.level = "root"  # Или "group" для корневого меню

        # Определяем данные группы
        if self.level == "group":
            self.data_group = self.data_skills.get(self.key)
        elif self.level == "detail":
            # Для деталей нам нужно найти группу. Это сложно без передачи группы.
            # Но пока предположим, что мы знаем группу или найдем её.
            # В текущей реализации data_group ищется по key, если key - это группа.
            pass
        else:
            # Root menu (список групп)
            self.data_group = None

        log.debug(f"Инициализирован {self.__class__.__name__} для персонажа ID={self.char_id} с ключом '{self.key}'.")

    async def render_skill_menu(self, data: FullCharacterDataDTO) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит меню навыков в зависимости от контекста (root, group, detail).
        """
        # В текущей реализации StatusBotOrchestrator вызывает это только для tab="skills" (root).
        # Но нам нужно поддержать и вложенность.

        if self.level == "root" or self.key == "skills":
            return self._render_root_menu(data)
        elif self.level == "group":
            return self.status_group_skill_message(data.skills)
        elif self.level == "detail":
            # Нам нужно знать группу.
            # Пока заглушка или поиск.
            return "Детали навыка (WIP)", InlineKeyboardBuilder().as_markup()

        return "Неизвестный контекст", InlineKeyboardBuilder().as_markup()

    def _render_root_menu(self, data: FullCharacterDataDTO) -> tuple[str, InlineKeyboardMarkup]:
        """Рендерит список групп навыков."""
        # В текущей реализации CharacterMenuUIService.get_skill_group_view делал это.
        # Мы перенесли это сюда.

        data_skills = self.data_skills.get("skills")
        if not isinstance(data_skills, dict):
            return "Данные о навыках не найдены.", InlineKeyboardBuilder().as_markup()
        items = data_skills.get("items")
        if not isinstance(items, dict):
            return "Предметы навыков не найдены.", InlineKeyboardBuilder().as_markup()

        char_name = data.character.name
        syb_name = self.actor_name

        text = SkillF.group_skill(data=items, char_name=char_name, actor_name=syb_name)

        # Клавиатура групп
        kb = InlineKeyboardBuilder()
        for key, value in items.items():
            callback_data = StatusSkillsCallback(char_id=self.char_id, level="group", key=key).pack()
            kb.button(text=value, callback_data=callback_data)
        kb.adjust(2)

        # Навигация
        # back_callback = StatusNavCallback(char_id=self.char_id, key="bio").pack() # Удалено: не используется
        # Добавляем табы
        # ... (логика табов)

        return text or "Ошибка форматирования", kb.as_markup()

    def status_group_skill_message(self, character_skills: list[SkillProgressDTO]) -> tuple[str, InlineKeyboardMarkup]:
        """
        Формирует сообщение со списком навыков в выбранной группе.
        """
        if not self.data_group:
            return "Группа навыков не найдена", self._group_skill_kb([])
        group_items = self.data_group.get("items")
        if not isinstance(group_items, dict):
            return "Предметы группы навыков не найдены", self._group_skill_kb([])

        sor_list_dto = self._sorted_group_skill(character_skills=character_skills, group_item=group_items)

        text = SkillF.format_skill_list_in_group(
            char_id=self.char_id, data_group=self.data_group, data_skill=sor_list_dto, actor_name=self.actor_name
        )

        kb = self._group_skill_kb(sor_list_dto)

        return text or "Ошибка форматирования", kb

    def status_detail_skill_message(
        self, group_key: str, skills_dto: list[SkillProgressDTO]
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Формирует сообщение с детальной информацией о конкретном навыке.
        """
        skill_dto = self._sort_detail_skill_data(skills_dto)
        if not skill_dto:
            return "Информация о навыке не найдена.", self._detail_kb(group_key, None)

        skill_display = SkillCal.get_skill_display_info(progress_dto=skill_dto)

        if not self.data_group:
            return "Группа навыков не найдена", self._detail_kb(group_key, skill_dto)

        text = SkillF.format_detail_skill_message(
            data=self.data_group, skill_dto=skill_dto, skill_display=skill_display, actor_name=self.actor_name
        )

        kb = self._detail_kb(group_key=group_key, skill_dto=skill_dto)

        return text or "Ошибка форматирования", kb

    def _detail_kb(self, group_key: str, skill_dto: SkillProgressDTO | None) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()

        if skill_dto:
            button_texts = {
                SkillProgressState.PLUS: "[ ➕ Повышать ]",
                SkillProgressState.PAUSE: "[ ⏸️ Пауза ]",
                SkillProgressState.MINUS: "[ ➖ Понижать ]",
            }
            # current_state = skill_dto.progress_state # В DTO пока нет progress_state, нужно добавить или заглушку
            # Предположим PAUSE
            current_state = SkillProgressState.PAUSE

            for state_enum in [SkillProgressState.PLUS, SkillProgressState.PAUSE, SkillProgressState.MINUS]:
                if state_enum != current_state:
                    kb.button(
                        text=button_texts[state_enum],
                        callback_data=SkillModeCallback(
                            char_id=self.char_id, skill_key=skill_dto.skill_key, new_mode=state_enum.value
                        ).pack(),
                    )
            kb.adjust(2)

        back_callback = StatusSkillsCallback(
            char_id=self.char_id,
            level="group",
            key=group_key,
        ).pack()
        kb.row(InlineKeyboardButton(text="[ ◀️ Назад к навыкам ]", callback_data=back_callback))

        return kb.as_markup()

    def _group_skill_kb(self, sor_list_dto: list[SkillProgressDTO]) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        if self.data_group:
            data_items = self.data_group.get("items")
            if isinstance(data_items, dict):
                for skill in sor_list_dto:
                    callback_data = StatusSkillsCallback(
                        char_id=self.char_id, level="detail", key=skill.skill_key
                    ).pack()
                    button_text = data_items.get(skill.skill_key)
                    if button_text:
                        kb.button(text=button_text, callback_data=callback_data)
        kb.adjust(2)

        back_callback = StatusNavCallback(
            char_id=self.char_id,
            key="skills",
        ).pack()
        kb.row(InlineKeyboardButton(text="[ ◀️ Назад к группам ]", callback_data=back_callback))
        return kb.as_markup()

    def _sorted_group_skill(
        self, character_skills: list[SkillProgressDTO], group_item: dict[str, str]
    ) -> list[SkillProgressDTO]:
        view_data = []
        for skill in character_skills:
            # skill.is_unlocked нет в DTO, нужно добавить или считать True
            if skill.skill_key in group_item:
                view_data.append(skill)
        return view_data

    def _sort_detail_skill_data(self, skills_dto: list[SkillProgressDTO]) -> SkillProgressDTO | None:
        for skill_dto in skills_dto:
            if self.key == skill_dto.skill_key:
                return skill_dto
        return None
