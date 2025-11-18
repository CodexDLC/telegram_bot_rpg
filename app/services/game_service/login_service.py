# app/services/game_service/login_service.py
from typing import Any

from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError

from app.services.core_service.manager.account_manager import account_manager
from database.repositories import get_character_repo
from database.session import get_async_session


class LoginService:
    """
    Сервис-Оркестратор для входа персонажа в игровой мир.
    ВЫПОЛНЯЕТ бизнес-логику, ВОЗВРАЩАЕТ ДАННЫЕ.
    НЕ отвечает за UI или логику перемещения.
    """

    def __init__(self, char_id: int, state_data: dict[str, Any]):
        self.char_id = char_id
        self.state_data = state_data
        log.debug(f"Инициализирован LoginService для char_id={self.char_id}")

    # --- ПУБЛИЧНЫЙ МЕТОД (для Хэндлера) ---

    async def handle_login(self) -> tuple[str, str] | str | None:
        """
        Главный метод входа. Проверяет SQL и загружает/создает сессию Redis.

        Returns:
            tuple[str, str] | None: (state, location_id) или None в случае
                                    ошибки (например, не пройден туториал).
        """

        # 1. Проверяем SQL (холодное хранилище)
        game_stage = await self._check_sql_game_stage()
        if game_stage != "in_game":
            log.warning(f"Попытка логина char_id={self.char_id} не из 'in_game' (stage: {game_stage})")
            return game_stage

        # 2. Загружаем/создаем сессию в Redis (горячее хранилище)
        (state, loc_id) = await self._load_or_create_redis_session()

        # 3. ВСЕ. Просто возвращаем данные.
        log.info(f"Логин char_id={self.char_id} успешен. Состояние: {state}:{loc_id}")
        return state, loc_id

    async def _check_sql_game_stage(self) -> str | None:
        """Проверяет game_stage персонажа в SQL базе."""
        try:
            async with get_async_session() as session:
                char_repo = get_character_repo(session)
                character_dto = await char_repo.get_character(self.char_id)
                if character_dto:
                    return character_dto.game_stage
            return None
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQL при проверке game_stage для char_id={self.char_id}: {e}")
            return None

    async def _load_or_create_redis_session(self) -> tuple[str, str]:
        """Загружает или создает 'ac:char_id' в Redis."""

        if await account_manager.account_exists(self.char_id):
            # Вход существующего игрока
            data = await account_manager.get_account_data(self.char_id)
            if data:
                state = data.get("state", "world")
                loc_id = data.get("location_id", "portal_plats")
                log.debug(f"Загружена сессия Redis для char_id={self.char_id} (state={state})")
                return state, loc_id
            else:
                # На случай, если аккаунт удалился между `exists` и `get`
                log.warning(
                    f"Аккаунт char_id={self.char_id} не найден в Redis, хотя `exists` вернул True. Создаем новый."
                )
                return await self._create_redis_session()
        else:
            # Первый вход игрока
            return await self._create_redis_session()

    async def _create_redis_session(self) -> tuple[str, str]:
        """Создает новую сессию в Redis."""
        log.info(f"Первый вход для char_id={self.char_id}. Создание сессии Redis...")
        start_loc_id = "portal_plats"
        initial_data = {
            "state": "world",
            "location_id": start_loc_id,
            "prev_state": "world",
            "prev_location_id": start_loc_id,
        }
        await account_manager.create_account(self.char_id, initial_data)
        return "world", start_loc_id
