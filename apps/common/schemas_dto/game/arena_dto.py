from typing import Any, Literal

from pydantic import BaseModel, Field


class ArenaQueueResponse(BaseModel):
    """
    Ответ на запрос постановки/отмены очереди на арене.
    """

    status: Literal["joined", "cancelled", "error"]
    gs: int | None = None
    message: str = ""


class ArenaMatchResponse(BaseModel):
    """
    Ответ на запрос проверки статуса матча.
    """

    session_id: str | None = None
    is_shadow: bool = False
    status: Literal["found", "waiting", "created_shadow", "error"]
    metadata: dict[str, Any] = Field(default_factory=dict)
