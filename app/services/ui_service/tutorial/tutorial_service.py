import logging
import random
from typing import Optional, List, Dict, Tuple, Any

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO
from app.resources.texts.buttons_callback import Buttons, GameStage
from app.resources.texts.game_messages.tutorial_messages import TutorialEventsData, TutorialMessages
from app.services.game_service.skill.skill_service import CharacterSkillsService
from database.repositories import get_character_stats_repo, get_skill_rate_repo, get_skill_progress_repo, \
    get_character_repo
from database.session import get_async_session

log = logging.getLogger(__name__)


class TutorialService:
    """
    Сервис для управления туториалом по созданию персонажа.

    Этот класс инкапсулирует логику интерактивного квеста, в ходе которого
    определяются стартовые характеристики персонажа. Он управляет пулом
    событий, подсчетом бонусов и взаимодействием с базой данных.
    """

    def __init__(
            self,
            char_id: int,
            pool_size: int = 4,
            event_pool: Optional[List[Dict]] = None,
            sim_text_count: int = 0,
            bonus_dict: Optional[Dict[str, int]] = None
    ):
        """
        Инициализирует сервис туториала.

        Args:
            char_id (int): ID персонажа, проходящего туториал.
            pool_size (int): Количество случайных событий для квеста.
            event_pool (Optional[List[Dict]]): Пул событий, восстановленный из FSM.
                Если None, создается новый.
            sim_text_count (int): Счетчик шагов, восстановленный из FSM.
            bonus_dict (Optional[Dict[str, int]]): Словарь с бонусами,
                восстановленный из FSM.
        """
        self.char_id = char_id
        self.pool_size = pool_size
        self.event_pool = event_pool if event_pool is not None else self._get_event_pool()
        self.sim_text_count = sim_text_count
        self.bonus_dict = bonus_dict if bonus_dict is not None else {}
        self.buttons = Buttons

    def get_restart_stats(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Возвращает данные для перезапуска туториала.

        Returns:
            Tuple[str, InlineKeyboardMarkup]: Текст и клавиатура для начала.
        """
        text = TutorialMessages.TUTORIAL_PROMPT_TEXT
        kb = self._tutorial_kb(self.buttons.TUTORIAL_START_BUTTON)
        return text, kb

    def get_data_animation_steps(self) -> Tuple[Tuple, InlineKeyboardMarkup]:
        """
        Возвращает данные для анимации подсчета результатов.

        Returns:
            Tuple[Tuple, InlineKeyboardMarkup]: Кортеж "кадров" для анимации
            и финальная клавиатура.
        """
        animation_steps = TutorialMessages.TUTORIAL_ANALYSIS_TEXT
        final_markup = self._tutorial_kb(TutorialMessages.TUTORIAL_ANALYSIS_BUTTON)
        return animation_steps, final_markup

    def get_next_step(self) -> Optional[Tuple[str, InlineKeyboardMarkup]]:
        """
        Извлекает следующее событие из пула и форматирует его.

        Если события в пуле закончились, это сигнализирует о завершении
        квестовой части туториала.

        Returns:
            Optional[Tuple[str, InlineKeyboardMarkup]]: Кортеж с текстом и
            клавиатурой для следующего шага, или None, если шаги закончились.
        """
        self.sim_text_count += 1
        try:
            event_data = self.event_pool.pop(0)
        except IndexError:
            log.debug("TutorialService: Пул событий пуст.")
            return None  # Сигнал для хэндлера о завершении.

        return self._format_step(event_data)

    def _format_step(self, event_data: dict) -> Tuple[str, InlineKeyboardMarkup]:
        """Форматирует данные события в текст и клавиатуру."""
        text_event = event_data.get("text", "")
        kb_data = event_data.get("buttons", {})
        text = TutorialEventsData.SIMULATION_TEXT_TEMPLATE.format(
            number=self.sim_text_count,
            text_event=text_event
        )
        kb = self._tutorial_kb(kb_data)
        return text, kb

    def add_bonus(self, choice_key: str):
        """
        Добавляет бонусы к характеристикам на основе выбора пользователя.

        Args:
            choice_key (str): Ключ выбора, полученный из callback-данных.
        """
        bonus = TutorialEventsData.TUTORIAL_LOGIC_POOL.get(choice_key)
        if bonus:
            for stat, bonus_value in bonus.items():
                self.bonus_dict[stat] = self.bonus_dict.get(stat, 0) + bonus_value

    def get_fsm_data(self) -> Dict[str, Any]:
        """
        Собирает данные сервиса для сохранения в FSM.

        Это позволяет "заморозить" состояние туториала между шагами.

        Returns:
            Dict[str, Any]: Словарь с данными для `state.update_data()`.
        """
        return {
            "event_pool": self.event_pool,
            "sim_text_count": self.sim_text_count,
            "bonus_dict": self.bonus_dict,
            "char_id": self.char_id
        }

    def _get_event_pool(self) -> List[Dict]:
        """Создает новый случайный пул событий."""
        event_pool = random.sample(TutorialEventsData.TUTORIAL_EVENT_POOL, self.pool_size)
        log.debug(f"Создан новый пул из {self.pool_size} событий: {event_pool}")
        return event_pool

    @staticmethod
    def _tutorial_kb(data: Dict[str, str]) -> InlineKeyboardMarkup:
        """Универсальный сборщик клавиатур для туториала."""
        kb = InlineKeyboardBuilder()
        if data:
            for key, value in data.items():
                kb.button(text=value, callback_data=key)
            kb.adjust(1)
        return kb.as_markup()

    async def update_stats_und_get(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Финализирует характеристики в БД и возвращает финальное сообщение.

        Returns:
            Tuple[str, InlineKeyboardMarkup]: Текст с итоговыми
            характеристиками и клавиатура для подтверждения.
        """
        final_stats_obj = await self._finalize_stats_in_db()

        if final_stats_obj:
            final_stats_for_text = final_stats_obj.model_dump()
        else:
            log.error(f"Не удалось финализировать статы для {self.char_id}")
            # Создаем заглушку, чтобы избежать падения.
            final_stats_for_text = {k: "N/A" for k in CharacterStatsReadDTO.model_fields.keys()}

        text = TutorialMessages.TUTORIAL_COMPLETE_TEXT.format(**final_stats_for_text)
        kb = self._tutorial_kb(TutorialMessages.TUTORIAL_CONFIRM_BUTTONS)
        return text, kb

    async def _finalize_stats_in_db(self) -> Optional[CharacterStatsReadDTO]:
        """
        Атомарно обновляет БД: финализирует статы, создает навыки, обновляет этап игры.

        Returns:
            Optional[CharacterStatsReadDTO]: DTO с финальными характеристиками
            или None в случае ошибки.
        """
        async with get_async_session() as session:
            # Используем сервис игровой логики для инкапсуляции сложных операций.
            char_service = CharacterSkillsService(
                stats_repo=get_character_stats_repo(session),
                rate_repo=get_skill_rate_repo(session),
                progress_repo=get_skill_progress_repo(session)
            )
            final_stats_obj = await char_service.finalize_tutorial_stats(
                character_id=self.char_id,
                bonus_stats=self.bonus_dict
            )
            # Обновляем этап игры персонажа, чтобы он не попал в туториал снова.
            char_repo = get_character_repo(session)
            await char_repo.update_character_game_stage(
                self.char_id, GameStage.TUTORIAL_SKILL
            )
            await session.commit()  # Фиксируем все изменения в транзакции.
            return final_stats_obj
