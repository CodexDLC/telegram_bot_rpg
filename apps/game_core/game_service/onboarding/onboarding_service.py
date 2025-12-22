import json

from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories.ORM.characters_repo_orm import CharactersRepoORM
from apps.common.schemas_dto.character_dto import CharacterOnboardingUpdateDTO, Gender
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.redis_service import RedisService


class OnboardingService:
    def __init__(self, session: AsyncSession, redis_service: RedisService):
        self.repo = CharactersRepoORM(session)
        self.account_manager = AccountManager(redis_service)

    async def save_character(self, char_id: int, name: str, gender: Gender) -> bool:
        """
        Сохраняет данные персонажа после завершения онбординга.
        Обновляет данные в PostgreSQL и Redis.
        """
        # 1. Пишем в Postgres
        update_dto = CharacterOnboardingUpdateDTO(name=name, gender=gender, game_stage="tutorial")
        await self.repo.update_character_onboarding(char_id, update_dto)

        # 2. Пишем в Redis
        # Формируем JSON для поля bio
        bio_data = {"name": name, "gender": gender}

        # Обновляем поля аккаунта: bio как JSON-строка, location_id отдельно
        await self.account_manager.update_account_fields(
            char_id,
            {
                "bio": json.dumps(bio_data, ensure_ascii=False),
                "location_id": "52_52",  # Дефолтный спавн
            },
        )
        return True
