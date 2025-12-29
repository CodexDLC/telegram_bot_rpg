import json

from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories.ORM.characters_repo_orm import CharactersRepoORM
from apps.common.schemas_dto.character_dto import CharacterOnboardingUpdateDTO, CharacterShellCreateDTO, Gender
from apps.common.schemas_dto.game_state_enum import GameState
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.redis_service import RedisService


class OnboardingService:
    def __init__(self, session: AsyncSession, redis_service: RedisService):
        self.repo = CharactersRepoORM(session)
        self.account_manager = AccountManager(redis_service)

    async def create_shell(self, user_id: int) -> int:
        """
        Создает пустую оболочку персонажа в БД.
        """
        shell_dto = CharacterShellCreateDTO(user_id=user_id)
        return await self.repo.create_character_shell(shell_dto)

    async def finalize_character(self, char_id: int, user_id: int, name: str, gender: Gender) -> None:
        """
        Обновляет данные персонажа и инициализирует кэш.
        """
        # 1. Обновляем данные в БД
        update_dto = CharacterOnboardingUpdateDTO(name=name, gender=gender, game_stage="tutorial")
        await self.repo.update_character_onboarding(char_id, update_dto)

        # 2. Пишем в Redis (инициализируем кэш аккаунта)
        bio_data = {"name": name, "gender": gender}
        location_data = {"current": "52_52", "prev": "52_52"}

        await self.account_manager.update_account_fields(
            char_id,
            {
                # user_id не пишем, он в БД
                "bio": json.dumps(bio_data, ensure_ascii=False),
                "location": json.dumps(location_data),
                "state": GameState.SCENARIO,
            },
        )
