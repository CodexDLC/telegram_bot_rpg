#app/services/ui_service/tutorial/tutorial_service_skill.py
import logging
from typing import Tuple, Union, List, Dict, Any

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.texts.game_messages.tutorial_messages_skill import TUTORIAL_SKILL_EVENTS
from app.resources.keyboards.callback_data import TutorialQuestCallback

log = logging.getLogger(__name__)


class TutorialServiceSkills:
    """
    Сервис для управления UI и логикой туториала по выбору навыков персонажа.

    Этот класс инкапсулирует логику интерактивного квеста, в ходе которого
    игрок делает выборы, определяющие стартовые навыки и характеристики
    его персонажа. Он отвечает за формирование текстовых сообщений и
    кнопок на каждом шаге туториала.
    """

    def __init__(self, skills_db: list[str]= None, callback_data: TutorialQuestCallback = None):
        """
        Инициализирует сервис на основе данных обратного вызова.

        Args:
            skills_db: Список для сбора выбранных пользователем навыков.
            callback_data: Объект CallbackData, содержащий текущее состояние
                           туториала (фазу, ветку, значение). Если None,
                           инициализируется начальное состояние.
        """
        self.data_pool = TUTORIAL_SKILL_EVENTS
        self.skills_db = skills_db

        if callback_data:
            self.phase = callback_data.phase
            self.branch = callback_data.branch
            self.value = callback_data.value
        else:
            self.phase = None
            self.branch = None
            self.value = None

        log.debug(
            f"TutorialServiceSkills initialized with state: "
            f"phase='{self.phase}', branch='{self.branch}', value='{self.value}'"
        )

    def _add_skill_db(self):
        """
        Добавляет выбранный навык в базу данных навыков персонажа.

        Метод проверяет, был ли инициализирован список навыков, и если да,
        добавляет в него текущее значение (`self.value`), которое представляет
        собой выбор пользователя на данном шаге. Навыки "none" не добавляются.
        """
        if self.skills_db is not None and self.value and self.value != "none":
            log.debug(f"Adding skill '{self.value}' to skills_db.")
            self.skills_db.append(self.value)
            log.debug(f"skills_db is now: {self.skills_db}")
        else:
            log.debug(f"Skipped adding skill. skills_db is None or value is '{self.value}'.")

    def get_skills_db(self) -> List[str]:
        """
        Возвращает список накопленных навыков.

        Returns:
            Список строковых идентификаторов навыков, выбранных
            пользователем в ходе туториала.
        """
        log.debug(f"Returning skills_db: {self.skills_db}")
        return self.skills_db

    def _get_branch_step1(self, branch: str, phase: str) -> Dict[str, Any]:
        """
        Извлекает данные для шага туториала по ветке и фазе.

        Args:
            branch: Идентификатор текущей ветки квеста.
            phase: Идентификатор текущей фазы в ветке.

        Returns:
            Словарь с данными для указанного шага.

        Raises:
            ValueError: Если данные для указанной ветки или фазы не найдены.
        """
        log.debug(f"Getting data for branch='{branch}', phase='{phase}'")
        branch_data = self.data_pool.get(branch)
        if branch_data is None:
            log.error(f"Branch '{branch}' not found in data pool.")
            raise ValueError(f"Branch '{branch}' not found")

        phase_data = branch_data.get(phase)
        if phase_data is None:
            log.error(f"Phase '{phase}' not found in branch '{branch}'.")
            raise ValueError(f"Phase '{phase}' not found in branch '{branch}'")

        return phase_data

    def _get_branch_step2(self, branch: str, phase: str, value: str) -> Dict[str, Any]:
        """
        Проверяет корректность пути и извлекает данные для шага туториала.

        Эта функция проверяет, что для данной ветки (branch), фазы (phase)
        и предыдущего выбора (value) существует запись в data_pool.
        Возвращает данные, относящиеся к конкретному выбору.

        Args:
            branch: Идентификатор текущей ветки квеста.
            phase: Идентификатор текущей фазы в ветке.
            value: Значение, уточняющее выбор на предыдущем шаге (для валидации).

        Returns:
            Словарь с данными для указанного выбора (value_data).

        Raises:
            ValueError: Если данные для указанной комбинации не найдены.
        """
        log.debug(f"Validating and getting data for branch='{branch}', phase='{phase}', value='{value}'")
        branch_data = self.data_pool.get(branch)
        if branch_data is None:
            log.error(f"Branch '{branch}' not found in data pool.")
            raise ValueError(f"Branch '{branch}' not found")

        phase_data = branch_data.get(phase)
        if phase_data is None:
            log.error(f"Phase '{phase}' not found in branch '{branch}'.")
            raise ValueError(f"Phase '{phase}' not found in branch '{branch}'")

        value_data = phase_data.get(value)
        if value_data is None:
            log.error(f"Value '{value}' not found in phase '{phase}' of branch '{branch}'.")
            raise ValueError(f"Value '{value}' not found")

        return value_data

    def get_start_data(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Возвращает данные для самого первого шага туториала.

        Returns:
            Кортеж, содержащий текст приветственного сообщения и
            клавиатуру с первыми вариантами выбора.
        """
        log.debug("Getting start data for the tutorial.")
        data = self.data_pool.get("start_skill_phase")

        text = data.get("text")
        kb = self._step_inline_kb(data.get("buttons"))

        return text, kb

    def get_next_data(self) -> Tuple[Union[str, List], InlineKeyboardMarkup]:
        """
        Определяет и возвращает данные для следующего шага туториала.

        На основе текущего состояния (phase, branch, value) определяет,
        какой контент и клавиатуру показать пользователю дальше.

        Returns:
            Кортеж, содержащий текст или лог боя и клавиатуру
            со следующими вариантами выбора.

        Raises:
            ValueError: Если не удается определить следующий шаг на основе
                        текущего состояния.
        """
        log.debug(f"Getting next data for state: phase='{self.phase}', branch='{self.branch}', value='{self.value}'")

        self._add_skill_db()

        if self.phase == "step_1":
            log.debug("Processing 'step_1'.")
            data = self._get_branch_step1(branch=self.branch, phase=self.phase)
            text = data.get("text")
            kb = self._step_inline_kb(data.get("buttons"))
            return text, kb

        elif self.phase == "step_2":
            log.debug("Processing 'step_2'.")
            data = self._get_branch_step2(branch=self.branch, phase=self.phase, value=self.value)
            text = data.get("text")
            kb = self._step_inline_kb(data.get("buttons"))
            return text, kb

        elif self.phase == "step_3":
            log.debug("Processing 'step_3'.")
            data = self._get_branch_step2(branch=self.branch, phase=self.phase, value=self.value)
            text_or_list: list[tuple[str, float]] = data.get("combat_log")
            kb = self._step_inline_kb(data.get("buttons"))
            return text_or_list, kb

        elif self.phase == "finale":
            log.debug("Processing 'finale'.")
            data = self._get_branch_step1(branch=self.phase, phase=self.value)
            text = data.get("text")
            kb = self._step_inline_kb(data.get("buttons"))
            return text, kb
        else:
            log.error(f"Could not determine next step for phase: '{self.phase}'")
            raise ValueError(f"Не получилось вернуть данные для фазы '{self.phase}'")

    def _step_inline_kb(self, buttons: dict) -> InlineKeyboardMarkup:
        """
        Создает инлайн-клавиатуру на основе словаря кнопок.

        Анализирует текущее состояние туториала для корректного
        формирования CallbackData для каждой кнопки.

        Args:
            buttons: Словарь, где ключи - это строки с данными для колбэка,
                     а значения - текст на кнопках.

        Returns:
            Готовый объект инлайн-клавиатуры.
        """
        kb = InlineKeyboardBuilder()
        log.debug(f"Building keyboard for state: branch='{self.branch}'")

        for key_str, text in buttons.items():
            parts = key_str.split(":")
            phase = parts[0]
            value = parts[1]

            if self.branch is None:
                # Состояние 1: Начало. Ключ вида "step_1:path_melee"
                # phase="step_1", branch="path_melee", value="none"
                log.debug(f"Creating START callback: phase='{phase}', branch='{value}'")
                cb = TutorialQuestCallback(phase=phase, branch=value, value="none")

            elif self.branch == "finale":
                # Состояние 2: Финал. Ключ вида "p_end:mining"
                # phase="p_end", branch="none", value="mining"
                log.debug(f"Creating FINALE callback: phase='{phase}', value='{value}'")
                cb = TutorialQuestCallback(phase=phase, branch="none", value=value)

            else:
                # Состояние 3: Середина квеста. Ключ вида "step_2:light_armor"
                # phase="step_2", branch=self.branch, value="light_armor"
                log.debug(f"Creating MIDDLE callback: phase='{phase}', branch='{self.branch}', value='{value}'")
                cb = TutorialQuestCallback(phase=phase, branch=self.branch, value=value)

            kb.button(text=text, callback_data=cb.pack())

        kb.adjust(1)
        return kb.as_markup()
