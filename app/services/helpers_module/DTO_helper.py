#
import logging
from dataclasses import asdict, is_dataclass


from app.resources.models.character_dto import CharacterReadDTO, CharacterStatsReadDTO

log = logging.getLogger(__name__)

DTO_MAP = {
    "character": CharacterReadDTO,
    "characters": CharacterReadDTO, # для списка
    "characters_stats": CharacterStatsReadDTO

}


async def fsm_store(value)-> dict | list[dict]:
    """Сохраняет dataclass, список dataclass'ов или обычные данные в FSM."""
    if is_dataclass(value):
        log.debug(f"fsm_store вернул {asdict(value)}")
        value = asdict(value)
    elif isinstance(value, list):
        log.debug(f"fsm_store вернул список {value}")
        value = [asdict(v) if is_dataclass(v) else v for v in value]
    return value


async def fsm_load_auto(state, key: str):
    """Загружает dataclass, список dataclass'ов или обычные данные из FSM."""
    data = await state.get_data()
    value = data.get(key)

    dto_class = DTO_MAP.get(key)

    if not dto_class or value is None:
        return value

    if isinstance(value, list):
        log.debug(f"fsm_load_auto вернул список {dto_class}")
        return [dto_class(**v) if isinstance(v, dict) else v for v in value]
    elif isinstance(value, dict):
        log.debug(f"fsm_load_auto вернул {dto_class}")
        return dto_class(**value)
    return value
