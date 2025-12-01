from sqlalchemy.ext.asyncio import AsyncSession

# Импортируем под-сервисы
from app.services.game_service.arena.service_1v1 import Arena1v1Service


class ArenaService:
    """
    ФАСАД (Main Entry Point) для всех механик Арены.
    Изолирует хэндлеры от конкретных реализаций (1v1, Group, Tournament).
    """

    def __init__(self, session: AsyncSession, char_id: int):
        self.session = session
        self.char_id = char_id

        # Подключаем "рабочих лошадок"
        # Делаем их приватными (_), чтобы хэндлер не лез в них напрямую
        self._service_1v1 = Arena1v1Service(session, char_id)

    async def join_queue(self, mode: str) -> int | None:
        """
        Вход в очередь. Возвращает GS или None.
        """
        if mode == "1v1":
            return await self._service_1v1.join_queue()

        # elif mode == "group": ...

        return None

    async def check_match(self, mode: str, attempt: int) -> str | None:
        """
        Проверка статуса поиска (для поллинга).
        Возвращает session_id, если бой найден.
        """
        if mode == "1v1":
            return await self._service_1v1.check_and_match(attempt)
        return None

    async def create_shadow_battle(self, mode: str) -> str:
        """
        Принудительное создание боя с Тенью (при таймауте).
        """
        if mode == "1v1":
            return await self._service_1v1.create_shadow_battle()
        return ""

    async def cancel_queue(self, mode: str) -> bool:
        """Отмена поиска."""
        if mode == "1v1":
            await self._service_1v1.cancel_queue()
            return True
        return False
