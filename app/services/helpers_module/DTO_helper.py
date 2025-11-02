#
import logging

from pydantic import BaseModel

from app.resources.schemas_dto.character_dto import CharacterReadDTO, CharacterStatsReadDTO
from app.resources.schemas_dto.skill import SkillProgressDTO

log = logging.getLogger(__name__)

DTO_MAP = {
    "character": CharacterReadDTO,
    "characters": CharacterReadDTO, # для списка
    "characters_stats": CharacterStatsReadDTO,
    "character_progress" : SkillProgressDTO

}


async def fsm_store(value) -> dict | list[dict]:
    """Сохраняет dataclass, список dataclass'ов или обычные данные в FSM."""

    if isinstance(value, BaseModel):
        value = value.model_dump(mode='json')
        log.debug(f"fsm_store вернул {value}")
    elif isinstance(value, list) and all(isinstance(list_item, BaseModel) for list_item in value):
        value = [v.model_dump(mode='json') for v in value]  # Применяем и для списков
        log.debug(f"fsm_store вернул список {value}")
    return value


async def fsm_load_auto(state, key: str):
    """Загружает dataclass, список dataclass'ов или обычные данные из FSM."""
    data = await state.get_data()
    value = data.get(key)

    dto_class = DTO_MAP.get(key)

    if not dto_class or value is None:
        return value

    return await fsm_convector(value, key)


async def fsm_convector(value: dict, key: str):

    dto_class = DTO_MAP.get(key)

    if not dto_class or value is None:
        return value

    if isinstance(value, list):
        log.debug(f"fsm_convector вернул список {dto_class}")
        return [dto_class.model_validate(v) if isinstance(v, dict) else v for v in value]
    elif isinstance(value, dict):
        log.debug(f"fsm_convector вернул {dto_class}")
        return dto_class.model_validate(value)
    return value
