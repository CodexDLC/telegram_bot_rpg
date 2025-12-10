# app/services/ui_service/tutorial/tutorial_service_skill.py
from typing import Any, cast

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.keyboards.callback_data import LobbySelectionCallback, TutorialQuestCallback
from apps.bot.resources.texts.buttons_callback import GameStage
from apps.bot.resources.texts.game_messages.tutorial_messages_skill import (
    TUTORIAL_PHASE_SKILL,
    TUTORIAL_SKILL_EVENTS,
    TUTORIAL_SKILL_FINALE,
)
from apps.common.database.repositories import CharactersRepoORM, SkillProgressRepo


class TutorialServiceSkills:
    """
    Сервис для управления UI и логикой туториала по выбору навыков персонажа.

    Этот класс инкапсулирует логику интерактивного квеста, в ходе которого
    игрок делает выборы, определяющие стартовые навыки и характеристики
    его персонажа. Он отвечает за формирование текстовых сообщений и
    кнопок на каждом шаге туториала.
    """

    def __init__(self, skills_db: list[str] | None = None, callback_data: TutorialQuestCallback | None = None):
        """
        Инициализирует сервис на основе данных обратного вызова.

        Args:
            skills_db: Список для сбора выбранных пользователем навыков.
            callback_data: Объект CallbackData, содержащий текущее состояние
                           туториала (фазу, ветку, значение). Если None,
                           инициализируется начальное состояние.
        """
        self.data_pool = TUTORIAL_SKILL_EVENTS
        self.data_final = TUTORIAL_SKILL_FINALE
        self.skills_db: list[str] | None = skills_db

        if callback_data:
            self.phase: str | None = callback_data.phase
            self.branch: str | None = callback_data.branch
            self.value: str | None = callback_data.value
        else:
            self.phase = None
            self.branch = None
            self.value = None

        log.debug(
            f"TutorialServiceSkills initialized with state: "
            f"phase='{self.phase}', branch='{self.branch}', value='{self.value}'"
        )

    def _add_skill_db(self, value: str | None = None) -> None:
        """
        Добавляет выбранный навык в базу данных навыков персонажа.

        Метод проверяет, был ли инициализирован список навыков, и если да,
        добавляет в него текущее значение (`self.value`), которое представляет
        собой выбор пользователя на данном шаге. Навыки "none" не добавляются.
        """
        if value is None:
            value = self.value

        if self.skills_db is not None and value and value != "none":
            log.debug(f"Adding skill '{value}' to skills_db.")
            self.skills_db.append(value)
            log.debug(f"skills_db is now: {self.skills_db}")
        else:
            log.debug(f"Skipped adding skill. skills_db is None or value is '{value}'.")

    def get_skills_db(self) -> list[str] | None:
        """
        Возвращает список накопленных навыков.

        Returns:
            Список строковых идентификаторов навыков, выбранных
            пользователем в ходе туториала.
        """
        log.debug(f"Returning skills_db: {self.skills_db}")
        return self.skills_db

    def _get_branch_step1(self, branch: str, phase: str) -> dict[str, Any]:
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
        if not isinstance(branch_data, dict):
            log.error(f"Branch '{branch}' not found in data pool or is not a dict.")
            raise ValueError(f"Branch '{branch}' not found")

        phase_data = branch_data.get(phase)
        if not isinstance(phase_data, dict):
            log.error(f"Phase '{phase}' not found in branch '{branch}' or is not a dict.")
            raise ValueError(f"Phase '{phase}' not found in branch '{branch}'")

        return phase_data

    def _get_branch_step2(self, branch: str, phase: str, value: str) -> dict[str, Any]:
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
        if not isinstance(branch_data, dict):
            log.error(f"Branch '{branch}' not found in data pool or is not a dict.")
            raise ValueError(f"Branch '{branch}' not found")

        phase_data = branch_data.get(phase)
        if not isinstance(phase_data, dict):
            log.error(f"Phase '{phase}' not found in branch '{branch}' or is not a dict.")
            raise ValueError(f"Phase '{phase}' not found in branch '{branch}'")

        value_data = phase_data.get(value)
        if not isinstance(value_data, dict):
            log.error(f"Value '{value}' not found in phase '{phase}' of branch '{branch}' or is not a dict.")
            raise ValueError(f"Value '{value}' not found")

        return value_data

    def get_start_data(self) -> tuple[str, InlineKeyboardMarkup] | tuple[None, None]:
        """
        Возвращает данные для самого первого шага туториала.

        Returns:
            Кортеж, содержащий текст приветственного сообщения и
            клавиатуру с первыми вариантами выбора.
        """
        log.debug("Getting start data for the tutorial.")
        data = self.data_pool.get("start_skill_phase")
        if not isinstance(data, dict):
            return None, None

        text = data.get("text")
        buttons = data.get("buttons")
        if not isinstance(text, str) or not isinstance(buttons, dict):
            return None, None
        kb = self._step_inline_kb(buttons)

        return text, kb

    def get_next_data(self) -> tuple[str | list[Any], InlineKeyboardMarkup] | tuple[None, None]:
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

        if not self.phase or not self.branch or not self.value:
            raise ValueError("Invalid state for get_next_data")

        data: dict[str, Any] | None = None
        text_or_list: str | list[Any] | None = None

        if self.phase == "step_1":
            log.debug("Processing 'step_1'.")
            data = self._get_branch_step1(branch=self.branch, phase=self.phase)
            self._add_skill_db(value=TUTORIAL_PHASE_SKILL.get(self.branch))
            text_or_list = data.get("text")

        elif self.phase == "step_2":
            log.debug("Processing 'step_2'.")
            data = self._get_branch_step2(branch=self.branch, phase=self.phase, value=self.value)
            self._add_skill_db()
            text_or_list = data.get("text")

        elif self.phase == "step_3":
            log.debug("Processing 'step_3'.")
            data = self._get_branch_step2(branch=self.branch, phase=self.phase, value=self.value)
            self._add_skill_db()
            text_or_list = data.get("combat_log")

        elif self.phase == "finale":
            log.debug("Processing 'finale'.")
            data = self._get_branch_step1(branch=self.phase, phase=self.value)
            self._add_skill_db()
            text_or_list = data.get("text")

        elif self.phase == "p_end":
            log.debug("Processing 'p_end'.")
            data = self._get_branch_step1(branch=self.phase, phase=self.value)
            self._add_skill_db()
            text_or_list = data.get("text")

        else:
            log.error(f"Could not determine next step for phase: '{self.phase}'")
            raise ValueError(f"Не получилось вернуть данные для фазы '{self.phase}'")

        if data and text_or_list:
            buttons = data.get("buttons")
            if isinstance(buttons, dict):
                kb = self._step_inline_kb(buttons)
                return text_or_list, kb

        return None, None

    def get_awakening_data(
        self,
        char_id: int,
        final_choice_key: str,  # <- Добавил этот аргумент
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Формирует финальное "пробуждающее" сообщение и клавиатуру.

        Использует self.data_final (TUTORIAL_SKILL_FINALE) для получения
        шаблона текста и данных кнопки. Форматирует текст, подставляя
        {choice_name}, и создает единственную кнопку с LobbySelectionCallback,
        ведущую к "логину" (пробуждению).

        Args:
            char_id (int): ID персонажа (для "вшивания" в callback).
            final_choice_key (str): Ключ финального выбора (e.g., "mining"),
                                     используется для форматирования текста.

        Returns:
            Tuple[str, InlineKeyboardMarkup]: Отформатированный текст и
                                              финальная клавиатура.
        """
        log.debug(f"Подготовка 'awakening_data' для char_id={char_id} с выбором '{final_choice_key}'")

        kb = InlineKeyboardBuilder()

        text_template = self.data_final.get("text", "")
        button_data = self.data_final.get("button", {})

        # Убедимся, что text_template - это строка
        if isinstance(text_template, list):
            # 1. Объединяем список в строку. Используем cast, чтобы mypy знал, что мы работаем со списком строк.
            text_template = "\n".join(cast(list[str], text_template))

        # 2. Гарантируем, что text_template имеет тип str, даже если он был Any из словаря
        if not isinstance(text_template, str):
            text_template = str(text_template)

        # Проверка, что final_choice_key является строкой
        safe_choice_name = str(final_choice_key) if final_choice_key is not None else "неизвестный выбор"

        # Теперь mypy уверен, что text_template - это str
        text = text_template.format(choice_name=safe_choice_name)

        action = button_data.get("action") if isinstance(button_data, dict) else None
        button_text = button_data.get("text") if isinstance(button_data, dict) else "Продолжить"

        if action and isinstance(button_text, str):
            callback = LobbySelectionCallback(
                action=action,
                char_id=char_id,
            ).pack()
            kb.button(text=button_text, callback_data=callback)
            kb.adjust(1)

        return text, kb.as_markup()

    def _step_inline_kb(self, buttons: dict[str, Any]) -> InlineKeyboardMarkup:
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
                log.debug(f"Creating START callback: phase='{phase}', branch='{value}'")
                cb = TutorialQuestCallback(phase=phase, branch=value, value="none")

            elif self.branch == "finale":
                log.debug(f"Creating FINALE callback: phase='{phase}', value='{value}'")
                cb = TutorialQuestCallback(phase=phase, branch="none", value=value)

            else:
                log.debug(f"Creating MIDDLE callback: phase='{phase}', branch='{self.branch}', value='{value}'")
                cb = TutorialQuestCallback(phase=phase, branch=self.branch, value=value)

            kb.button(text=text, callback_data=cb.pack())

        kb.adjust(1)
        return kb.as_markup()

    async def finalize_skill_selection(self, char_id: int, session: AsyncSession) -> None:
        """
        Финализирует туториал по навыкам, управляя собственной транзакцией.

        Этот метод открывает собственную сессию 'get_async_session' и
        выполняет в ней две критические операции:
        1. Разблокирует (is_unlocked=True) все навыки из `self.skills_db`.
        2. Переводит персонажа на следующий игровой этап (IN_GAME).

        'get_async_session' автоматически выполнит commit при успехе
        или rollback при любой ошибке.

        Args:
            char_id (int): ID персонажа для обновления.

        Raises:
            SQLAlchemyError: Если любая из DB-операций завершится
                             неудачно (будет поймана и проброшена).
            Exception: Если произойдет любая другая ошибка (будет поймана
                       и проброшена).
        """

        if not self.skills_db:
            log.warning(f"Попытка финализировать навыки для char_id={char_id}, но 'self.skills_db' пуст.")
            return

        log.info(f"Начало финализации туториала навыков для char_id={char_id} в БД (внутренняя сессия)...")

        try:
            progress_repo = SkillProgressRepo(session)
            char_repo = CharactersRepoORM(session)

            log.debug(f"Шаг 1/2: Обновление 'is_unlocked=True' для char_id={char_id}. Навыки: {self.skills_db}")
            await progress_repo.update_skill_unlocked_state(
                character_id=char_id, skill_key_list=self.skills_db, state=True
            )

            log.debug(f"Шаг 2/2: Обновление 'game_stage' на '{GameStage.IN_GAME}' для char_id={char_id}.")
            await char_repo.update_character_game_stage(character_id=char_id, game_stage=GameStage.IN_GAME)

            log.info(f"Финализация навыков и game_stage для char_id={char_id} УСПЕШНО ЗАКОММИЧЕНА.")

        except (SQLAlchemyError, Exception) as e:
            log.exception(f"Ошибка при финализации навыков для char_id={char_id}. ТРАНЗАКЦИЯ ОТКАТИЛАСЬ. Ошибка: {e}")
            await session.rollback()
            raise
