from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.texts.buttons_callback import Buttons
from apps.bot.resources.texts.game_messages.lobby_messages import LobbyMessages
from apps.common.database.repositories.ORM.characters_repo_orm import CharactersRepoORM
from apps.common.schemas_dto import CharacterOnboardingUpdateDTO


class OnboardingService:
    """
    Сервис для управления процессом создания нового персонажа (onboarding).

    Предоставляет методы для получения текстов, клавиатур и обновления
    данных персонажа в базе данных на всех этапах его создания:
    от выбора пола до ввода имени и начала туториала.
    """

    def __init__(self, user_id: int, char_id: int | None = None):
        """
        Инициализирует сервис создания персонажа.

        Args:
            user_id (int): ID пользователя Telegram.
            char_id (Optional[int]): ID создаваемого персонажа.
                Может быть None на начальных этапах, но должен быть установлен
                перед обновлением БД.
        """
        self.user_id = user_id
        self.buttons = Buttons
        self.new_char = LobbyMessages.NewCharacter
        self.char_id = char_id
        log.debug(f"Инициализирован {self.__class__.__name__} для user_id={self.user_id}, char_id={char_id}.")

    def get_data_start_creation_content(self) -> tuple[str, InlineKeyboardMarkup]:
        """
        Возвращает данные (текст и клавиатуру) для первого шага: выбор пола.

        Returns:
            Tuple[str, InlineKeyboardMarkup]: Текст с предложением выбрать
            пол и клавиатура с вариантами.
        """
        log.debug(
            f"Получение данных для стартового контентного сообщения создания персонажа для user_id={self.user_id}."
        )
        text = self.new_char.GENDER_CHOICE
        kb = self._start_creation_kb()
        return text, kb

    def get_data_start_gender(self, gender_callback: str) -> tuple[str, str, str]:
        """
        Обрабатывает выбор пола и возвращает данные для следующего шага (ввод имени).

        Args:
            gender_callback (str): Callback-данные от кнопки выбора пола
                (e.g., "gender:male").

        Returns:
            Tuple[str, str, str]: Кортеж, содержащий:
                - Текст с предложением ввести имя.
                - Отображаемое название пола для UI (e.g., "Мужчина").
                - Значение пола для записи в БД (e.g., "male").
        """
        log.debug(f"Обработка выбора пола '{gender_callback}' для user_id={self.user_id}.")
        text = self.new_char.NAME_INPUT
        gender_display = self.buttons.GENDER.get(gender_callback, "Не указан")
        gender_db = gender_callback.split(":")[-1]
        log.debug(f"Выбран пол: UI='{gender_display}', DB='{gender_db}'.")
        return text, gender_display, gender_db

    def get_data_choosing_name(self) -> str:
        """
        Возвращает текст для этапа ввода имени.

        Returns:
            str: Текст с предложением ввести имя.
        """
        log.debug(f"Получение текста для этапа ввода имени для user_id={self.user_id}.")
        return self.new_char.NAME_INPUT

    async def update_character_db(self, char_update_dto: CharacterOnboardingUpdateDTO, session: AsyncSession) -> None:
        """
        Обновляет данные создаваемого персонажа в базе данных.

        Args:
            char_update_dto (CharacterOnboardingUpdateDTO): DTO с данными
                (имя, пол, этап игры) для обновления.
            session (AsyncSession): Сессия базы данных.

        Returns:
            None

        Raises:
            ValueError: Если `char_id` не был установлен.
            Exception: В случае ошибки при взаимодействии с БД.
        """
        if not self.char_id:
            log.error(f"Попытка обновить персонажа для user_id={self.user_id}, но char_id не установлен.")
            raise ValueError("char_id must be set before updating the character.")

        log.info(f"Запрос на обновление данных персонажа {self.char_id} в БД для user_id={self.user_id}.")
        log.debug(f"Данные для обновления: {char_update_dto.model_dump_json()}")

        char_repo = CharactersRepoORM(session)
        try:
            await char_repo.update_character_onboarding(character_id=self.char_id, character_data=char_update_dto)
            log.info(f"Данные персонажа {self.char_id} успешно обновлены в БД.")
        except Exception as e:
            log.exception(f"Ошибка при обновлении данных персонажа {self.char_id} для user_id={self.user_id}: {e}")
            await session.rollback()
            raise

    def get_data_start(self, name: str, gender: str) -> tuple[str, InlineKeyboardMarkup]:
        """
        Возвращает данные для финального сообщения перед туториалом.

        Args:
            name (str): Имя созданного персонажа.
            gender (str): Отображаемое название пола.

        Returns:
            Tuple[str, InlineKeyboardMarkup]: Финальный текст и клавиатура
            для начала туториала.
        """
        log.debug(
            f"Получение данных для стартового сообщения туториала для персонажа '{name}' (user_id={self.user_id})."
        )
        text = self.new_char.FINAL_CONFIRMATION.format(name=name, gender=gender)
        kb = self._tutorial_kb()
        return text, kb

    def _start_creation_kb(self) -> InlineKeyboardMarkup:
        """Создает клавиатуру для выбора пола."""
        kb = InlineKeyboardBuilder()
        log.debug("Создание клавиатуры для выбора пола.")
        for key, value in self.buttons.GENDER.items():
            kb.button(text=value, callback_data=key)
        return kb.as_markup()

    def _tutorial_kb(self) -> InlineKeyboardMarkup:
        """Создает клавиатуру для начала туториала."""
        kb = InlineKeyboardBuilder()
        log.debug("Создание клавиатуры для начала туториала.")
        data = self.buttons.TUTORIAL_START_BUTTON
        if data:
            for key, value in data.items():
                kb.button(text=value, callback_data=key)
            kb.adjust(1)
        return kb.as_markup()
