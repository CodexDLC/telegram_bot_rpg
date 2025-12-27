from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories import get_character_repo
from apps.common.schemas_dto.character_dto import CharacterOnboardingUpdateDTO
from apps.common.schemas_dto.core_response_dto import CoreResponseDTO, GameStateHeader
from apps.common.schemas_dto.game_state_enum import GameState
from apps.common.schemas_dto.onboarding_dto import (
    OnboardingActionDTO,
    OnboardingDraftDTO,
    OnboardingStepEnum,
    OnboardingViewDTO,
)
from apps.common.schemas_dto.scenario_dto import ScenarioInitDTO
from apps.common.services.core_service.redis_service import RedisService
from apps.common.services.validators.character_validator import validate_character_name
from apps.game_core.game_service.onboarding.onboarding_session_manager import OnboardingSessionManager


class OnboardingCoreOrchestrator:
    """
    Оркестратор онбординга (Core Layer).
    Управляет процессом создания персонажа.
    """

    def __init__(self, session: AsyncSession, redis_service: RedisService):
        self.session = session
        self.repo = get_character_repo(session)
        self.manager = OnboardingSessionManager(redis_service)

    async def get_state(self, char_id: int) -> CoreResponseDTO[OnboardingViewDTO]:
        """
        Возвращает текущее состояние онбординга.
        """
        draft = await self.manager.get_draft(char_id)
        return self._build_response(draft)

    async def handle_action(self, char_id: int, action_dto: OnboardingActionDTO) -> CoreResponseDTO:
        """
        Обрабатывает действие пользователя.
        """
        draft = await self.manager.get_draft(char_id)
        error = None

        if action_dto.action == "start":
            draft.step = OnboardingStepEnum.NAME

        elif action_dto.action == "set_name":
            name = str(action_dto.value).strip()
            is_valid, err_msg = validate_character_name(name)

            if not is_valid:
                error = err_msg
            else:
                # Проверка уникальности в БД
                # TODO: Добавить метод is_name_taken в репозиторий
                # if await self.repo.is_name_taken(name):
                #     error = "Имя уже занято"
                # else:
                draft.name = name
                draft.step = OnboardingStepEnum.GENDER

        elif action_dto.action == "set_gender":
            gender = str(action_dto.value)
            if gender in ["male", "female"]:
                draft.gender = gender
                # Пропускаем расу и класс пока что
                draft.step = OnboardingStepEnum.CONFIRM
            else:
                error = "Некорректный пол"

        elif action_dto.action == "finalize" and draft.step == OnboardingStepEnum.CONFIRM:
            return await self._finalize(char_id, draft)

        # Сохраняем обновленный драфт
        await self.manager.update_draft(char_id, draft)

        return self._build_response(draft, error)

    async def _finalize(self, char_id: int, draft: OnboardingDraftDTO) -> CoreResponseDTO:
        """
        Финализирует создание персонажа.
        """
        if not draft.name or not draft.gender:
            return self._build_response(draft, error="Не все данные заполнены")

        # Обновляем персонажа в БД
        update_dto = CharacterOnboardingUpdateDTO(
            name=draft.name,
            gender=draft.gender,  # type: ignore
            game_stage="in_game",
        )

        try:
            await self.repo.update_character_onboarding(char_id, update_dto)
            # Очищаем драфт
            await self.manager.clear_draft(char_id)

            # Переход в Сценарий (Туториал)
            return CoreResponseDTO(
                header=GameStateHeader(current_state=GameState.SCENARIO),
                payload=ScenarioInitDTO(quest_key="tutorial_start", node_id="wake_up"),
            )
        except Exception as e:  # noqa: BLE001
            return self._build_response(draft, error=f"Ошибка сохранения: {e}")

    def _build_response(
        self, draft: OnboardingDraftDTO, error: str | None = None
    ) -> CoreResponseDTO[OnboardingViewDTO]:
        """
        Формирует ответ для UI.
        """
        view_dto = OnboardingViewDTO(step=draft.step, draft=draft, error=error)
        return CoreResponseDTO(header=GameStateHeader(current_state=GameState.ONBOARDING), payload=view_dto)
