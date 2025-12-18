from typing import Any

from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories import get_character_repo
from apps.common.schemas_dto.auth_dto import GameStage
from apps.common.services.core_service.manager.account_manager import AccountManager


class LoginService:
    """
    Сервис-оркестратор для обработки входа персонажа в игровой мир.

    Отвечает за проверку стадии игры персонажа в базе данных,
    загрузку или создание сессии персонажа в Redis.
    """

    def __init__(self, char_id: int, state_data: dict[str, Any], account_manager: AccountManager):
        """
        Инициализирует LoginService.

        Args:
            char_id: Уникальный идентификатор персонажа.
            state_data: Текущие данные FSM-состояния.
            account_manager: Менеджер аккаунтов.
        """
        self.char_id = char_id
        self.state_data = state_data
        self.account_manager = account_manager
        log.debug(f"LoginService | status=initialized char_id={self.char_id}")

    async def handle_login(self, session: AsyncSession) -> tuple[str, str] | str | None:
        """
        Основной метод для обработки процесса входа персонажа.

        Проверяет стадию игры персонажа в SQL, затем загружает или создает
        его сессию в Redis.

        Args:
            session: Асинхронная сессия базы данных.

        Returns:
            Кортеж `(state, location_id)` если вход успешен и персонаж находится
            в игровом мире.
            Строка `game_stage` если персонаж находится на стадии туториала или создания.
            None в случае критической ошибки.
        """
        game_stage = await self._check_sql_game_stage(session)
        if game_stage != GameStage.IN_GAME:
            log.info(f"LoginService | event=redirect_to_stage char_id={self.char_id} stage='{game_stage}'")
            return game_stage

        state, loc_id = await self._load_or_create_redis_session()

        log.info(f"LoginService | status=success char_id={self.char_id} state='{state}' location='{loc_id}'")
        return state, loc_id

    async def _check_sql_game_stage(self, session: AsyncSession) -> str | None:
        """
        Проверяет текущую стадию игры (`game_stage`) персонажа в SQL базе данных.

        Args:
            session: Асинхронная сессия базы данных.

        Returns:
            Строка, представляющая `game_stage` персонажа, или None, если персонаж не найден.
        """
        try:
            char_repo = get_character_repo(session)
            character_dto = await char_repo.get_character(self.char_id)
            if character_dto:
                return character_dto.game_stage
            log.warning(f"LoginService | status=failed reason='Character not found in DB' char_id={self.char_id}")
            return None
        except SQLAlchemyError:
            log.exception(
                f"LoginService | status=failed reason='SQLAlchemy error during game_stage check' char_id={self.char_id}"
            )
            return None

    async def _load_or_create_redis_session(self) -> tuple[str, str]:
        """
        Загружает существующую сессию персонажа из Redis или создает новую, если она отсутствует.

        Returns:
            Кортеж `(state, location_id)`, представляющий текущее состояние и локацию персонажа.
        """
        if await self.account_manager.account_exists(self.char_id):
            data = await self.account_manager.get_account_data(self.char_id)
            if data:
                state = data.get("state", "world")
                loc_id = data.get("location_id", "52_52")

                # Временная миграция для исправления неверного ID локации
                if loc_id == "town_hall_in":
                    log.warning(
                        f"LoginService | event=location_migration char_id={self.char_id} old='town_hall_in' new='town_hall_interior'"
                    )
                    loc_id = "town_hall_interior"
                    await self.account_manager.update_account_fields(self.char_id, {"location_id": loc_id})

                log.debug(
                    f"LoginService | event=redis_session_loaded char_id={self.char_id} state='{state}' location='{loc_id}'"
                )
                return state, loc_id
            else:
                log.warning(
                    f"LoginService | status=failed reason='Account data empty despite existence' char_id={self.char_id}"
                )
                return await self._create_redis_session()
        else:
            log.info(f"LoginService | event=redis_session_not_found action=create_new char_id={self.char_id}")
            return await self._create_redis_session()

    async def _create_redis_session(self) -> tuple[str, str]:
        """
        Создает новую сессию персонажа в Redis с начальными данными.

        Returns:
            Кортеж `(state, location_id)` новой сессии.
        """
        start_loc_id = "52_52"
        initial_data = {
            "state": "world",
            "location_id": start_loc_id,
            "prev_state": "world",
            "prev_location_id": start_loc_id,
        }
        await self.account_manager.create_account(self.char_id, initial_data)
        log.info(
            f"LoginService | event=redis_session_created char_id={self.char_id} state='world' location='{start_loc_id}'"
        )
        return "world", start_loc_id
