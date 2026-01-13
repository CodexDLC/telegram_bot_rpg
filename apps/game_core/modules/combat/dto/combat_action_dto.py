"""
DTO, описывающие Действия (Actions) и Сигналы.
"""

from typing import Any

from pydantic import BaseModel


class CombatMoveDTO(BaseModel):
    """
    "Пуля" (Intent) - заявка на ход от игрока.
    Хранится в RedisJSON (`moves:{char_id}`).
    """

    move_id: str  # Unique Short ID
    char_id: int  # Кто ходит

    # Зона хранения и Логика обработки
    strategy: str  # "item" | "instant" | "exchange"

    created_at: float  # Timestamp

    # Полиморфный контейнер данных
    payload: dict[str, Any]  # ItemPayload | InstantPayload | ExchangePayload

    # Результат резолвинга целей (заполняется Колектором)
    targets: list[int] | None = None


class CollectorSignalDTO(BaseModel):
    """
    Сигнал для триггера Колектора.
    Отправляется Роутером в очередь `arq:combat_collector`.
    """

    session_id: str
    char_id: int
    signal_type: str  # "check_immediate" | "check_timeout"
    move_id: str | None = None


class CombatActionResultDTO(BaseModel):
    """
    Результат принятия действия (для API).
    """

    success: bool
    move_id: str | None = None
    message: str | None = None
    error: str | None = None


class CombatActionDTO(BaseModel):
    """
    Задача для Воркера в очереди `q:actions`.
    Содержит полные данные мува (Cut & Paste).
    """

    action_type: str  # "item", "instant", "exchange", "forced"

    # Основной мув (Инициатор)
    move: CombatMoveDTO

    # Ответный мув (для exchange)
    partner_move: CombatMoveDTO | None = None

    is_forced: bool = False
