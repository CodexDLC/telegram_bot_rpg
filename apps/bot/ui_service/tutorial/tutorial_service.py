# app/services/ui_service/tutorial/tutorial_service.py
import random
from typing import Any

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.texts.buttons_callback import Buttons, GameStage
from apps.bot.resources.texts.game_messages.tutorial_messages import TutorialEventsData, TutorialMessages
from apps.common.database.repositories import (
    get_character_stats_repo,
    get_skill_progress_repo,
    get_skill_rate_repo,
)
from apps.common.database.repositories.ORM.characters_repo_orm import CharactersRepoORM
from apps.common.schemas_dto import CharacterStatsReadDTO
from apps.game_core.game_service.skill.skill_service import CharacterSkillsService


class TutorialServiceStats:
    """
    Сервис для управления UI и логикой туториала по созданию персонажа.

    Инкапсулирует логику интерактивного квеста, в ходе которого
    определяются стартовые характеристики персонажа.
    """

    def __init__(
        self,
        char_id: int,
        pool_size: int = 4,
        event_pool: list[dict] | None = None,
        sim_text_count: int = 0,
        bonus_dict: dict[str, int] | None = None,
    ):
        """
        Инициализирует сервис туториала.

        Args:
            char_id (int): ID персонажа.
            pool_size (int): Количество случайных событий для квеста.
            event_pool (Optional[List[Dict]]): Пул событий, восстановленный из FSM.
            sim_text_count (int): Счетчик шагов, восстановленный из FSM.
            bonus_dict (Optional[Dict[str, int]]): Словарь с бонусами из FSM.
        """
        self.char_id = char_id
        self.pool_size = pool_size
        self.event_pool = event_pool if event_pool is not None else self._get_event_pool()
        self.sim_text_count = sim_text_count if event_pool else 0
        self.bonus_dict = bonus_dict if bonus_dict is not None else {}
        self.buttons = Buttons
        log.debug(
            f"Инициализирован {self.__class__.__name__} для char_id={self.char_id}. Событий в пуле: {len(self.event_pool)}."
        )

    def get_restart_stats(self) -> tuple[str, InlineKeyboardMarkup]:
        """Возвращает данные для перезапуска туториала."""
        log.debug(f"Подготовка данных для перезапуска туториала для char_id={self.char_id}.")
        text = TutorialMessages.TUTORIAL_PROMPT_TEXT
        kb = self._tutorial_kb(self.buttons.TUTORIAL_START_BUTTON)
        return text, kb

    def get_data_animation_steps(self) -> tuple[tuple, InlineKeyboardMarkup]:
        """Возвращает данные для анимации подсчета результатов."""
        log.debug(f"Подготовка данных для анимации подсчета для char_id={self.char_id}.")
        animation_steps = TutorialMessages.TUTORIAL_ANALYSIS_TEXT
        final_markup = self._tutorial_kb(TutorialMessages.TUTORIAL_ANALYSIS_BUTTON)
        return animation_steps, final_markup

    def get_next_step(self) -> tuple[str, InlineKeyboardMarkup] | None:
        """
        Извлекает следующее событие из пула и форматирует его.

        Returns:
            Optional[Tuple[str, InlineKeyboardMarkup]]: Данные для следующего шага
            или None, если шаги закончились.
        """
        self.sim_text_count += 1
        try:
            event_data = self.event_pool.pop(0)
            log.debug(
                f"Извлечено событие #{self.sim_text_count} для char_id={self.char_id}. Осталось: {len(self.event_pool)}."
            )
            return self._format_step(event_data)
        except IndexError:
            log.info(f"Пул событий для char_id={self.char_id} исчерпан.")
            return None

    def _format_step(self, event_data: dict) -> tuple[str, InlineKeyboardMarkup]:
        """Форматирует данные события в текст и клавиатуру."""
        text_event = event_data.get("text", "")
        kb_data = event_data.get("buttons", {})
        text = TutorialEventsData.SIMULATION_TEXT_TEMPLATE.format(number=self.sim_text_count, text_event=text_event)
        kb = self._tutorial_kb(kb_data)
        return text, kb

    def add_bonus(self, choice_key: str) -> None:
        """Добавляет бонусы к характеристикам на основе выбора пользователя."""
        bonus = TutorialEventsData.TUTORIAL_LOGIC_POOL.get(choice_key)
        if bonus:
            for stat, bonus_value in bonus.items():
                self.bonus_dict[stat] = self.bonus_dict.get(stat, 0) + bonus_value
            log.debug(
                f"Для char_id={self.char_id} добавлен бонус {bonus} по ключу '{choice_key}'. Текущие бонусы: {self.bonus_dict}"
            )
        else:
            log.warning(f"Не найден бонус для ключа '{choice_key}' в TUTORIAL_LOGIC_POOL.")

    def get_fsm_data(self) -> dict[str, Any]:
        """Собирает данные сервиса для сохранения в FSM."""
        return {
            "event_pool": self.event_pool,
            "sim_text_count": self.sim_text_count,
            "bonus_dict": self.bonus_dict,
            "char_id": self.char_id,
        }

    def _get_event_pool(self) -> list[dict]:
        """Создает новый случайный пул событий."""
        log.debug(f"Создание нового пула событий размером {self.pool_size}.")
        event_pool = random.sample(TutorialEventsData.TUTORIAL_EVENT_POOL, self.pool_size)
        return event_pool

    @staticmethod
    def _tutorial_kb(data: dict[str, str]) -> InlineKeyboardMarkup:
        """Универсальный сборщик клавиатур для туториала."""
        kb = InlineKeyboardBuilder()
        if data:
            for key, value in data.items():
                kb.button(text=value, callback_data=key)
            kb.adjust(1)
        return kb.as_markup()

    async def finalize_stats(self, session: AsyncSession) -> tuple[str, InlineKeyboardMarkup]:
        """Финализирует характеристики в БД и возвращает финальное сообщение."""
        log.info(f"Начало финализации статов в БД для char_id={self.char_id}.")
        final_stats_obj = await self._finalize_stats_in_db(session)

        if final_stats_obj:
            final_stats_for_text = final_stats_obj.model_dump()
            log.info(f"Статы для char_id={self.char_id} успешно финализированы.")
        else:
            log.error(f"Не удалось финализировать статы для char_id={self.char_id}. Будет отображен текст-заглушка.")
            final_stats_for_text = {k: "N/A" for k in CharacterStatsReadDTO.model_fields}

        text = TutorialMessages.TUTORIAL_COMPLETE_TEXT.format(**final_stats_for_text)
        kb = self._tutorial_kb(TutorialMessages.TUTORIAL_CONFIRM_BUTTONS)
        return text, kb

    async def _finalize_stats_in_db(self, session: AsyncSession) -> CharacterStatsReadDTO | None:
        """Атомарно обновляет БД: статы, навыки, этап игры."""
        log.debug(f"Открытие сессии для финализации статов char_id={self.char_id}.")
        try:
            char_service = CharacterSkillsService(
                stats_repo=get_character_stats_repo(session),
                rate_repo=get_skill_rate_repo(session),
                progress_repo=get_skill_progress_repo(session),
            )
            final_stats_obj = await char_service.finalize_tutorial_stats(
                character_id=self.char_id, bonus_stats=self.bonus_dict
            )
            if not final_stats_obj:
                raise ValueError("finalize_tutorial_stats вернул None")

            char_repo = CharactersRepoORM(session)
            await char_repo.update_character_game_stage(self.char_id, GameStage.TUTORIAL_SKILL)
            log.debug(f"Игровой этап для char_id={self.char_id} обновлен на '{GameStage.TUTORIAL_SKILL}'.")
            log.info(f"Транзакция финализации статов для char_id={self.char_id} готова к коммиту.")
            return final_stats_obj
        except (SQLAlchemyError, ValueError) as e:
            log.exception(
                f"Ошибка во время финализации статов для char_id={self.char_id}. Откат транзакции. Ошибка: {e}"
            )
            await session.rollback()
            return None
