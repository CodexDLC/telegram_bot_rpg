from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from apps.common.schemas_dto.game_state_enum import GameState

T = TypeVar("T")


class GameStateHeader(BaseModel):
    """
    Мета-информация для навигации Бота.
    """

    current_state: GameState = Field(..., description="Куда переключить UI бота")
    previous_state: GameState | None = None
    transaction_id: str = Field(default_factory=str, description="Trace ID для логов")

    # Опционально: можно добавить error_code сюда, если header отвечает за статус
    error: str | None = None


class CoreResponseDTO(BaseModel, Generic[T]):
    """
    Базовый транспортный конверт.
    Наследовать его не обязательно, достаточно использовать Generic[T].
    """

    header: GameStateHeader
    payload: T | None = None
