from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories import get_character_repo
from apps.common.schemas_dto import CharacterReadDTO, CharacterShellCreateDTO


class LobbyCoreOrchestrator:
    """
    Оркестратор лобби (Core Layer).
    Отвечает за управление персонажами (создание, удаление, получение списка).
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.char_repo = get_character_repo(session)

    async def get_user_characters(self, user_id: int) -> list[CharacterReadDTO]:
        """Возвращает список персонажей пользователя."""
        characters = await self.char_repo.get_characters(user_id)
        return characters or []

    async def create_character_shell(self, user_id: int) -> int:
        """Создает оболочку персонажа и возвращает ID."""
        dto = CharacterShellCreateDTO(user_id=user_id)
        return await self.char_repo.create_character_shell(dto)

    async def delete_character(self, char_id: int) -> bool:
        """Удаляет персонажа."""
        try:
            await self.char_repo.delete_characters(char_id)
            return True
        except Exception:  # noqa: BLE001
            return False
