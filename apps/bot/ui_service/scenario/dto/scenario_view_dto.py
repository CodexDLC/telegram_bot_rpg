from pydantic import BaseModel

from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO


class ScenarioViewDTO(BaseModel):
    """
    DTO для передачи данных отображения сценария из оркестратора в хендлер.
    """

    content: ViewResultDTO
    is_terminal: bool = False
    node_key: str | None = None
