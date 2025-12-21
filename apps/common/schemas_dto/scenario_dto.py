from pydantic import BaseModel, Field


class ScenarioButtonDTO(BaseModel):
    """Схема кнопки действия."""

    label: str = Field(..., description="Текст на кнопке")
    action_id: str = Field(..., description="ID действия, который вернется в step_scenario")


class ScenarioPayloadDTO(BaseModel):
    """Основное тело ответа со сценой."""

    node_key: str = Field(..., description="ID текущей ноды")
    text: str = Field(..., description="Художественный текст без форматирования")
    status_bar: list[str] = Field(default_factory=list, description="Список строк для статус-бара")
    buttons: list[ScenarioButtonDTO] = Field(default_factory=list, description="Список доступных кнопок")
    is_terminal: bool = Field(default=False, description="Является ли сцена финальной (конец квеста)")


class ScenarioResponseDTO(BaseModel):
    """Финальный конверт ответа API."""

    status: str = Field(default="success")
    payload: ScenarioPayloadDTO
