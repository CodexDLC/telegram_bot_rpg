from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto.character_dto import Gender
from apps.common.schemas_dto.onboarding_dto import OnboardingButtonDTO, OnboardingResponseDTO
from apps.common.services.core_service.redis_service import RedisService
from apps.game_core.resources.onboarding_config import OnboardingConfig


class OnboardingCoreOrchestrator:
    def __init__(self, session: AsyncSession, redis_service: RedisService):
        self.session = session
        self.redis_service = redis_service

        # O(1) Диспетчер
        self._dispatch = {
            "start": self._get_gender_step,
            "set_gender": self._get_name_step,
            "set_name": self._get_confirm_step,
            "finalize": self._handle_finalize,  # Здесь будет вызов тяжелого сервиса
        }

    async def handle(self, action: str, **kwargs) -> OnboardingResponseDTO:
        method = self._dispatch.get(action, self._get_gender_step)
        # mypy не может вывести тип метода из словаря с разными сигнатурами,
        # поэтому используем Any или игнорируем ошибку, так как мы знаем, что делаем.
        return await method(**kwargs)  # type: ignore

    # --- Легкие методы (UI из словаря) ---

    async def _get_gender_step(self, **kwargs) -> OnboardingResponseDTO:
        step = OnboardingConfig.GENDER_STEP
        text = cast(str, step["text"])
        buttons_data = cast(list[dict[str, Any]], step["buttons"])
        return OnboardingResponseDTO(text=text, buttons=[OnboardingButtonDTO(**b) for b in buttons_data])

    async def _get_name_step(self, **kwargs) -> OnboardingResponseDTO:
        step = OnboardingConfig.NAME_STEP
        text = cast(str, step["text"])
        return OnboardingResponseDTO(text=text, buttons=[])

    async def _get_confirm_step(self, **kwargs) -> OnboardingResponseDTO:
        # Возвращаем шаблон текста, форматирование будет на стороне бота
        step = OnboardingConfig.CONFIRM_STEP
        text = cast(str, step["text"])
        buttons_data = cast(list[dict[str, Any]], step["buttons"])
        return OnboardingResponseDTO(text=text, buttons=[OnboardingButtonDTO(**b) for b in buttons_data])

    # --- Тяжелый метод (Мост к сервису) ---

    async def _handle_finalize(self, char_id: int, name: str, gender: Gender, **kwargs) -> OnboardingResponseDTO:
        # Вот тут мы создаем сервис и реально сохраняем данные
        from apps.game_core.game_service.onboarding.onboarding_service import OnboardingService

        service = OnboardingService(self.session, self.redis_service)

        await service.save_character(char_id, name, gender)

        # Возвращаем "Мостик" к сценарию
        step = OnboardingConfig.FINAL_BRIDGE
        text = cast(str, step["text"])
        buttons_data = cast(list[dict[str, Any]], step["buttons"])
        return OnboardingResponseDTO(text=text, buttons=[OnboardingButtonDTO(**b) for b in buttons_data])
