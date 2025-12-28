from typing import Any

from aiogram.fsm.context import FSMContext
from loguru import logger as log
from pydantic import BaseModel, ValidationError

from apps.common.schemas_dto import CharacterReadDTO, CharacterStatsReadDTO, SessionDataDTO, SkillProgressDTO

# Старый ключ (для совместимости, пока не вычистим)
FSM_CONTEXT_KEY = "session_context"

# Новые ключи
KEY_UI_COORDS = "ui_coords"  # Хранит {menu: {chat_id, msg_id}, content: {...}}
KEY_SESSION_DATA = "session_data"  # Хранит {user_id, char_id, actor_name}

DTO_MAP: dict[str, type[BaseModel]] = {
    "character": CharacterReadDTO,
    "characters": CharacterReadDTO,
    "character_stats": CharacterStatsReadDTO,
    "character_progress": SkillProgressDTO,
    FSM_CONTEXT_KEY: SessionDataDTO,
}
log.debug(f"DtoHelper | event=dto_map_initialized count={len(DTO_MAP)}")


async def fsm_store(value: Any) -> dict | list[dict] | Any:
    """
    Сериализует Pydantic модели (DTO) в словари для безопасного хранения в FSM.
    """
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    elif isinstance(value, list) and value and isinstance(value[0], BaseModel):
        return [v.model_dump(mode="json") for v in value]
    else:
        return value


async def fsm_load_auto(state: FSMContext, key: str) -> Any:
    """
    Автоматически загружает и десериализует данные из FSM в Pydantic модели.
    """
    data = await state.get_data()
    value = data.get(key)

    if value is None:
        return None

    return await fsm_converter(value, key)


async def fsm_converter(value: Any, key: str) -> Any:
    """
    Преобразует сырые данные (словарь/список) в Pydantic модель или список моделей.
    """
    dto_class = DTO_MAP.get(key)

    if not dto_class:
        return value

    try:
        if isinstance(value, list):
            return [dto_class.model_validate(v) if isinstance(v, dict) else v for v in value]
        elif isinstance(value, dict):
            return dto_class.model_validate(value)
        else:
            return value
    except (ValidationError, TypeError) as e:
        log.exception(f"DtoHelper | status=failed reason='Pydantic validation error' key='{key}' error='{e}'")
        return value
