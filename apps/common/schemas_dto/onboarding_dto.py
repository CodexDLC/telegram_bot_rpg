from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class OnboardingStepEnum(StrEnum):
    """Этапы создания персонажа."""

    WELCOME = "welcome"
    NAME = "name"
    GENDER = "gender"
    RACE = "race"
    CLASS = "class"
    CONFIRM = "confirm"


class OnboardingActionDTO(BaseModel):
    """
    DTO действия пользователя в онбординге.
    """

    action: str = Field(..., description="Тип действия (set_name, set_gender, finalize, etc.)")
    value: Any | None = Field(None, description="Значение (имя, пол, etc.)")


class OnboardingDraftDTO(BaseModel):
    """
    DTO черновика персонажа (хранится в Redis).
    """

    step: OnboardingStepEnum = OnboardingStepEnum.WELCOME
    name: str | None = None
    gender: str | None = None
    race: str | None = None
    class_id: str | None = None

    # Доп. поля, если нужны (например, распределенные статы)


class OnboardingViewDTO(BaseModel):
    """
    DTO для отрисовки UI онбординга.
    """

    step: OnboardingStepEnum
    draft: OnboardingDraftDTO
    error: str | None = None  # Сообщение об ошибке (например, "Имя занято")
    available_options: list[str] | None = None  # Список доступных опций (для рас, классов)
