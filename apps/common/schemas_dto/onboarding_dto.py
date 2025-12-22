from typing import Any

from pydantic import BaseModel


class OnboardingButtonDTO(BaseModel):
    label: str
    action: str
    value: Any = None
    is_scenario: bool = False  # Переключатель на движок квестов
    quest_key: str | None = None


class OnboardingResponseDTO(BaseModel):
    text: str  # Готовый отформатированный текст для игрока
    buttons: list[OnboardingButtonDTO] = []
    # next_state оставляем только если ты хочешь, чтобы бэк управлял FSM бота
