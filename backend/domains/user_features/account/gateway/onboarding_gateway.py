from typing import Any

from backend.core.exceptions import BaseAPIException
from backend.domains.user_features.account.services.onboarding_service import OnboardingService
from common.schemas.enums import CoreDomain
from common.schemas.onboarding import OnboardingActionEnum, OnboardingUIPayloadDTO
from common.schemas.response import CoreResponseDTO, GameStateHeader


class OnboardingGateway:
    """
    Gateway для Onboarding.
    Принимает запросы от клиента (через Bot Orchestrator), вызывает Service и возвращает DTO.
    """

    def __init__(self, service: OnboardingService):
        self.service = service

    async def handle_action(self, char_id: int, action: str, value: Any = None) -> CoreResponseDTO:
        """
        Обрабатывает действие пользователя.
        """
        try:
            payload: OnboardingUIPayloadDTO | None = None

            if action == OnboardingActionEnum.SET_NAME.value:
                payload = await self.service.set_name(char_id, str(value))

            elif action == OnboardingActionEnum.SET_GENDER.value:
                payload = await self.service.set_gender(char_id, str(value))

            elif action == OnboardingActionEnum.FINALIZE.value:
                await self.service.finalize(char_id)
                # Возвращаем редирект в сценарий
                return CoreResponseDTO(
                    header=GameStateHeader(current_state=CoreDomain.SCENARIO),
                    payload=None,  # Или Payload сценария
                )

            else:
                # Неизвестный экшен
                return self._error_response(f"Unknown action: {action}")

            # Если payload получен, возвращаем ONBOARDING
            if payload:
                return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.ONBOARDING), payload=payload)

            return self._error_response("Action returned no payload")

        except BaseAPIException as e:
            return self._error_response(e.detail)
        except Exception as e:  # noqa: BLE001
            return self._error_response(f"Handle action failed: {e}")

    async def resume(self, char_id: int) -> CoreResponseDTO:
        """
        Восстанавливает сессию (для LoginGateway).
        """
        try:
            payload = await self.service.resume_session(char_id)
            return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.ONBOARDING), payload=payload)
        except BaseAPIException as e:
            return self._error_response(e.detail)
        except Exception as e:  # noqa: BLE001
            return self._error_response(f"Resume failed: {e}")

    def _error_response(self, message: str) -> CoreResponseDTO:
        return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.ONBOARDING, error=message), payload=None)
