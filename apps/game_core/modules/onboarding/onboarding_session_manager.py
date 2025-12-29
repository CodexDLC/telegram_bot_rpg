import contextlib
import json

from apps.common.schemas_dto.onboarding_dto import OnboardingDraftDTO
from apps.common.services.core_service.redis_key import RedisKeys
from apps.common.services.core_service.redis_service import RedisService


class OnboardingSessionManager:
    """
    Менеджер сессии онбординга.
    Отвечает за хранение черновика персонажа в Redis.
    """

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service

    async def get_draft(self, char_id: int) -> OnboardingDraftDTO:
        """
        Получает черновик из Redis. Если нет - возвращает пустой.
        """
        key = RedisKeys.get_onboarding_draft_key(char_id)
        raw_data = await self.redis_service.get_value(key)

        if raw_data:
            with contextlib.suppress(Exception):
                data = json.loads(raw_data)
                return OnboardingDraftDTO(**data)

        # Если черновика нет или он битый, возвращаем новый
        return OnboardingDraftDTO()

    async def update_draft(self, char_id: int, draft: OnboardingDraftDTO) -> None:
        """
        Сохраняет черновик в Redis.
        """
        key = RedisKeys.get_onboarding_draft_key(char_id)
        json_data = draft.model_dump_json()
        # TTL 24 часа (чтобы можно было продолжить завтра)
        await self.redis_service.set_value(key, json_data, ttl=86400)

    async def clear_draft(self, char_id: int) -> None:
        """
        Удаляет черновик из Redis.
        """
        key = RedisKeys.get_onboarding_draft_key(char_id)
        await self.redis_service.delete_key(key)
