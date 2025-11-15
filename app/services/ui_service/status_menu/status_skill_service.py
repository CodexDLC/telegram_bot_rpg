# app/services/ui_service/status_skill_service.py
import logging
from typing import Any, Optional, Dict, Tuple, List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.game_data.status_menu.skill_group_data import SKILL_HIERARCHY
from app.resources.keyboards.status_callback import StatusSkillsCallback, StatusNavCallback
from app.resources.schemas_dto.skill import SkillProgressDTO
from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME

from app.services.ui_service.helpers_ui.skill_formatters import SkillFormatters as SkillF
from app.services.ui_service.base_service import BaseUIService
from app.services.game_service.skill.calculator_service import SkillCalculatorService as SkillCal

from database.repositories import get_skill_progress_repo
from database.session import get_async_session

log = logging.getLogger(__name__)


class CharacterSkillStatusService(BaseUIService):
    """
    Сервис для управления UI-логикой меню навыков персонажа.

    Отвечает за формирование текстовых сообщений и клавиатур для отображения
    информации о навыках персонажа на разных уровнях вложенности: от общего
    списка групп навыков до детальной информации о конкретном навыке.
    """

    def __init__(self,
                 char_id: int,
                 key: str,
                 state_data: Dict[str, Any],
                 syb_name: Optional[str] = None,
                 ):
        """
        Инициализирует сервис для работы с навыками персонажа.

        :param char_id: ID персонажа.
        :param key: Ключ для доступа к данным о группе навыков или конкретном навыке.
        :param state_data: Данные состояния FSM.
        :param syb_name: Имя персонажа (опционально).
        """
        super().__init__(char_id=char_id, state_data=state_data)
        self.actor_name = syb_name or DEFAULT_ACTOR_NAME
        self.data_skills = SKILL_HIERARCHY
        self.data_group = self.data_skills.get(key)
        self.key = key
        log.debug(f"Инициализирован {self.__class__.__name__} для персонажа ID={self.char_id} с ключом '{key}'.")

    def status_group_skill_message(
            self,
            character_skills: List[SkillProgressDTO]
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Формирует сообщение со списком навыков в выбранной группе.

        :param character_skills: Список DTO с прогрессом навыков персонажа.
        :return: Кортеж с текстом сообщения и клавиатурой.
        """
        log.debug(f"Формирование сообщения для группы навыков '{self.key}' для персонажа ID={self.char_id}.")
        sor_list_dto = self._sorted_group_skill(
            character_skills=character_skills,
            group_item=self.data_group.get("items")
        )

        text = SkillF.format_skill_list_in_group(
            char_id=self.char_id,
            data_group=self.data_group,
            data_skill=sor_list_dto,
            actor_name=self.actor_name
        )

        kb = self._group_skill_kb(sor_list_dto)

        return text, kb

    def status_detail_skill_message(self, group_key: str, skills_dto: List[SkillProgressDTO]) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Формирует сообщение с детальной информацией о конкретном навыке.

        :param group_key: Ключ родительской группы навыка.
        :param skills_dto: Список всех DTO навыков персонажа.
        :return: Кортеж с текстом сообщения и клавиатурой.
        """
        log.debug(f"Формирование детального сообщения для навыка '{self.key}' для персонажа ID={self.char_id}.")
        skill_dto = self._sort_detail_skill_data(skills_dto)
        if not skill_dto:
            log.warning(f"Не найден DTO для навыка '{self.key}' у персонажа ID={self.char_id}.")
            # Можно вернуть сообщение об ошибке или обработать иначе
            return "Информация о навыке не найдена.", self._detail_kb(group_key)

        skill_display = SkillCal.get_skill_display_info(progress_dto=skill_dto)

        log.debug(f"DTO навыка: {skill_dto}")
        log.debug(f"Отображаемые данные навыка: {skill_display}")

        text = SkillF.format_detail_skill_message(
            data=self.data_group,
            skill_dto=skill_dto,
            skill_display=skill_display,
            actor_name=self.actor_name
        )

        kb = self._detail_kb(group_key=group_key)

        return text, kb

    def _detail_kb(self, group_key: str) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру для детального просмотра навыка (кнопка "Назад").

        :param group_key: Ключ группы, к которой нужно вернуться.
        :return: Объект клавиатуры.
        """
        back_callback = StatusSkillsCallback(
            char_id=self.char_id,
            level="group",
            key=group_key,
        ).pack()
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="[ ◀️ Назад к навыкам ]", callback_data=back_callback)
            ]
        ])

    def _group_skill_kb(self, sor_list_dto: List[SkillProgressDTO]) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру для списка навыков в группе.

        :param sor_list_dto: Отсортированный список DTO навыков для отображения.
        :return: Объект клавиатуры.
        """
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

        # Кнопка "Назад" для возврата к списку групп навыков
        back_callback = StatusNavCallback(
            char_id=self.char_id,
            key="skills"  # Ключ Lvl 0, который показывает Lvl 1 (список групп)
        ).pack()

        kb.row(
            InlineKeyboardButton(text="[ ◀️ Назад к группам ]", callback_data=back_callback)
        )
        return kb.as_markup()

    def _sorted_group_skill(
            self,
            character_skills: List[SkillProgressDTO],
            group_item: Dict[str, str]
    ) -> List[SkillProgressDTO]:
        """
        Фильтрует и возвращает список разблокированных навыков для указанной группы.

        :param character_skills: Полный список DTO навыков персонажа.
        :param group_item: Словарь с элементами группы навыков.
        :return: Список отфильтрованных DTO.
        """
        view_data = []
        if group_item:
            for skill in character_skills:
                if skill.skill_key in group_item and skill.is_unlocked:
                    view_data.append(skill)
        return view_data

    def _sort_detail_skill_data(self, skills_dto: List[SkillProgressDTO]) -> Optional[SkillProgressDTO]:
        """
        Находит и возвращает DTO для конкретного навыка по его ключу.

        :param skills_dto: Список всех DTO навыков персонажа.
        :return: DTO искомого навыка или None, если не найден.
        """
        for skill_dto in skills_dto:
            if self.key == skill_dto.skill_key:
                return skill_dto
        return None

    async def get_list_skills_dto(self) -> Optional[List[SkillProgressDTO]]:
        """
        Асинхронно получает список всех DTO прогресса навыков для персонажа из базы данных.

        :return: Список DTO навыков или None, если навыки не найдены.
        :raises: Любое исключение, возникшее при работе с БД.
        """
        try:
            async with get_async_session() as session:
                skill_progress_repo = get_skill_progress_repo(session)
                skills_data = await skill_progress_repo.get_all_skills_progress(character_id=self.char_id)
                if skills_data:
                    log.debug(f"Найдено {len(skills_data)} навыков для персонажа ID={self.char_id}.")
                    return skills_data
                else:
                    log.warning(f"Навыки для персонажа ID={self.char_id} не найдены.")
                    return None
        except Exception as e:
            log.error(f"Ошибка при получении навыков из БД для персонажа ID={self.char_id}: {e}", exc_info=True)
            raise
