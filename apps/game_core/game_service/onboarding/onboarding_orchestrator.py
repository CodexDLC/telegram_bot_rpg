from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto.core_response_dto import CoreResponseDTO, GameStateHeader
from apps.common.schemas_dto.game_state_enum import GameState
from apps.common.schemas_dto.onboarding_dto import (
    OnboardingDraftDTO,
    OnboardingStepEnum,
    OnboardingViewDTO,
)
from apps.common.services.core_service.redis_service import RedisService
from apps.common.services.validators.character_validator import validate_character_name
from apps.game_core.game_service.onboarding.onboarding_service import OnboardingService
from apps.game_core.game_service.onboarding.onboarding_session_manager import OnboardingSessionManager

if TYPE_CHECKING:
    from apps.game_core.game_service.core_router import CoreRouter


class OnboardingCoreOrchestrator:
    """
    Оркестратор онбординга (Core Layer).
    Координирует процесс создания персонажа, используя Service и Manager.
    """

    def __init__(self, session: AsyncSession, redis_service: RedisService, core_router: "CoreRouter | None" = None):
        self.manager = OnboardingSessionManager(redis_service)
        self.service = OnboardingService(session, redis_service)
        self.core_router = core_router
        self.session = session  # Нужно для роутера

    # --- Protocol Implementation ---

    async def get_entry_point(self, char_id: int, action: str, context: dict[str, Any]) -> Any:
        """
        Единая точка входа (CoreOrchestratorProtocol).
        """
        # В онбординге char_id - это user_id (пока не создан персонаж)
        user_id = char_id

        if action == "view" or action == "resume":
            draft = await self.manager.get_draft(user_id)
            return OnboardingViewDTO(step=draft.step, draft=draft)

        elif action == "start":
            # Сброс драфта
            await self.manager.clear_draft(user_id)
            draft = await self.manager.get_draft(user_id)
            return OnboardingViewDTO(step=draft.step, draft=draft)

        raise ValueError(f"Unknown action for Onboarding: {action}")

    # --- Public API ---

    async def get_state(self, user_id: int) -> CoreResponseDTO[OnboardingViewDTO]:
        """
        Возвращает текущее состояние онбординга.
        """
        draft = await self.manager.get_draft(user_id)
        return self._build_response(draft)

    async def handle_action(self, user_id: int, action: str, value: Any = None) -> CoreResponseDTO:
        """
        Обрабатывает действие пользователя.
        """
        draft = await self.manager.get_draft(user_id)
        error = None

        if action == "start":
            # Создаем болванку в БД, если её нет
            if not draft.char_id:
                try:
                    char_id = await self.service.create_shell(user_id)
                    draft.char_id = char_id
                except Exception as e:  # noqa: BLE001
                    return self._build_response(draft, error=f"Ошибка создания: {e}")

            draft.step = OnboardingStepEnum.NAME

        elif action == "set_name":
            name = str(value).strip()
            is_valid, err_msg = validate_character_name(name)

            if not is_valid:
                error = err_msg
            else:
                draft.name = name
                draft.step = OnboardingStepEnum.GENDER

        elif action == "set_gender":
            gender = str(value)
            if gender in ["male", "female"]:
                draft.gender = gender
                draft.step = OnboardingStepEnum.CONFIRM
            else:
                error = "Некорректный пол"

        elif action == "finalize" and draft.step == OnboardingStepEnum.CONFIRM:
            return await self._finalize(user_id, draft)

        # Сохраняем обновленный драфт
        await self.manager.update_draft(user_id, draft)

        return self._build_response(draft, error)

    async def _finalize(self, user_id: int, draft: OnboardingDraftDTO) -> CoreResponseDTO:
        """
        Финализирует создание персонажа и переходит в Туториал.
        """
        if not draft.name or not draft.gender or not draft.char_id:
            return self._build_response(draft, error="Не все данные заполнены")

        try:
            # Обновляем персонажа
            await self.service.finalize_character(draft.char_id, user_id, draft.name, draft.gender)  # type: ignore

            # Очищаем драфт
            await self.manager.clear_draft(user_id)

            # Переход в Сценарий (Туториал) через CoreRouter с REAL char_id
            if self.core_router:
                payload = await self.core_router.get_initial_view(
                    target_state=GameState.SCENARIO,
                    char_id=draft.char_id,  # Используем ID из драфта
                    session=self.session,
                    action="initialize",
                    context={"quest_key": "awakening_rift"},
                )

                return CoreResponseDTO(header=GameStateHeader(current_state=GameState.SCENARIO), payload=payload)

            # Fallback
            return CoreResponseDTO(header=GameStateHeader(current_state=GameState.SCENARIO), payload=None)

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
