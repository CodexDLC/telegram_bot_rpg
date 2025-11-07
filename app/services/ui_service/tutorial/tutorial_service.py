import logging
import random

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
    Класс для хранения методов режима стартового туториала с формированием персонажа
    """

    def __init__(
            self,
            char_id: int,
            pool_size: int =4,
            event_pool: list[dict] | None = None,
            sim_text_count: int = 0,
            bonus_dict: dict[str, int] | None = None
    ):

        self.char_id = char_id
        self.pool_size = pool_size

        # Если FSM не передал нам event_pool, создаем новый
        if event_pool is None:
            self.event_pool = self._get_event_pool()
        else:
            self.event_pool = event_pool

        # Используем то, что пришло из FSM
        self.sim_text_count = sim_text_count

        # Если FSM не передал bonus_dict, создаем новый
        if bonus_dict is None:
            self.bonus_dict = {}
        else:
            self.bonus_dict = bonus_dict

        self.buttons = Buttons


    def get_restart_stats(self):


        text = TutorialMessages.TUTORIAL_PROMPT_TEXT

        kb = self._tutorial_kb(
            self.buttons.TUTORIAL_START_BUTTON
        )

        return text, kb

    def get_data_animation_steps(self):

        animation_steps = TutorialMessages.TUTORIAL_ANALYSIS_TEXT
        final_markup = self._tutorial_kb(TutorialMessages.TUTORIAL_ANALYSIS_BUTTON)

        return animation_steps, final_markup


    def get_next_step(self) -> tuple[str, InlineKeyboardMarkup] | tuple[None, None]:
        """
        Главный публичный метод.
        Извлекает следующее событие, форматирует его и возвращает text, kb.
        Если события кончились, возвращает (None, None).
        """

        # 1. Увеличиваем счетчик шага
        self.sim_text_count += 1

        # 2. Извлекаем СЛЕДУЮЩИЙ ивент из пула
        try:
            event_data = self.event_pool.pop(0)
        except IndexError:
            log.debug("TutorialService: Пул событий пуст. Сигнализируем о завершении.")
            return None, None  # Сигнал для хэндлера, что квест окончен

        # 3. Передаем данные во внутренний метод-форматтер
        text, kb = self._format_step(event_data)

        return text, kb

    def _format_step(self, event_data: dict) -> tuple[str, InlineKeyboardMarkup]:
        """
        Внутренний метод. Только форматирует текст и клавиатуру.
        """
        text_event = event_data.get("text", "")
        kb_data = event_data.get("buttons", {})

        sim_text_template = TutorialEventsData.SIMULATION_TEXT_TEMPLATE

        text = sim_text_template.format(
            number=self.sim_text_count,
            text_event=text_event
        )
        kb = self._tutorial_kb(kb_data)

        return text, kb

    def add_bonus(self, choice_key: str):
        """
        Добавляет стат-бонусы к self.bonus_dict на основе выбора игрока.
        """
        data = TutorialEventsData.TUTORIAL_LOGIC_POOL
        bonus = data.get(choice_key)

        if bonus:
            for stat, bonus_value in bonus.items():
                if stat in self.bonus_dict:
                    self.bonus_dict[stat] += bonus_value
                else:
                    self.bonus_dict[stat] = bonus_value



    def get_fsm_data(self) -> dict:
        """
        Возвращает словарь с ДАННЫМИ, которые нужно сохранить в FSM.
        """
        return {
            "event_pool": self.event_pool,
            "sim_text_count": self.sim_text_count,
            "bonus_dict": self.bonus_dict,
            "char_id": self.char_id
        }

    def _get_event_pool(self) -> list[dict]:  # <--- Аргумент 'number' не нужен
        """
        Возвращает N случайных событий из пула.
        (Оставил приватным, т.к. он нужен только в __init__)
        """
        TUTORIAL_EVENT_POOL = TutorialEventsData.TUTORIAL_EVENT_POOL

        event_pool = random.sample(TUTORIAL_EVENT_POOL, self.pool_size)

        log.debug(f"Список из {self.pool_size} случайных событий: {event_pool}")
        return event_pool

    @staticmethod
    def _tutorial_kb(data: dict[str, str]) -> InlineKeyboardMarkup:
        """
        Возвращает Inline-клавиатуру с кнопкой для туториал.
        """
        kb = InlineKeyboardBuilder()
        if data:
            for key, value in data.items():
                kb.button(text=value, callback_data=key)
                kb.adjust(1)
        return kb.as_markup()

    async def update_stats_und_get(self):
        """
        Внешний метод (лицевой):
        1. Вызывает внутренний метод для обновления БД.
        2. Форматирует результат в (text, kb) для хэндлера.
        """

        # 1. Вызываем внутренний метод
        final_stats_obj = await self._finalize_stats_in_db()

        # 2. Форматируем результат
        if final_stats_obj:
            # Превращаем DTO в словарь для .format()
            final_stats_for_text = {
                "strength": final_stats_obj.strength,
                "perception": final_stats_obj.perception,
                "endurance": final_stats_obj.endurance,
                "charisma": final_stats_obj.charisma,
                "intelligence": final_stats_obj.intelligence,
                "agility": final_stats_obj.agility,
                "luck": final_stats_obj.luck,
            }
        else:
            # Обработка ошибки, если БД ничего не вернула
            log.error(f"Не удалось финализировать статы для {self.char_id}, _finalize_stats_in_db вернул None")
            # Создаем "заглушку", чтобы .format() не упал
            final_stats_for_text = {
                "strength": "N/A", "perception": "N/A", "endurance": "N/A",
                "charisma": "N/A", "intelligence": "N/A", "agility": "N/A", "luck": "N/A",
            }

        text = TutorialMessages.TUTORIAL_COMPLETE_TEXT.format(**final_stats_for_text)
        kb = self._tutorial_kb(TutorialMessages.TUTORIAL_CONFIRM_BUTTONS)

        return text, kb

    async def _finalize_stats_in_db(self) -> CharacterStatsReadDTO | None:
        """
        Внутренний метод: Атомарно обновляет БД.
        Финализирует статы, создает навыки, обновляет стадию.
        Возвращает DTO с финальными статами.
        """
        async with get_async_session() as session:
            # 1. Создаем сервис бизнес-логики
            char_service = CharacterSkillsService(
                stats_repo=get_character_stats_repo(session),
                rate_repo=get_skill_rate_repo(session),
                progress_repo=get_skill_progress_repo(session)
            )

            # 2. Выполняем финализацию
            final_stats_obj = await char_service.finalize_tutorial_stats(
                character_id=self.char_id,
                bonus_stats=self.bonus_dict
            )

            # 3. Обновляем стадию игры
            char_repo = get_character_repo(session)
            await char_repo.update_character_game_stage(
                self.char_id, GameStage.TUTORIAL_SKILL)

            # 4. Возвращаем результат
            return final_stats_obj

