from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from pydantic import BaseModel, ValidationError

from apps.common.schemas_dto import CharacterReadDTO, CharacterStatsReadDTO, SessionDataDTO, SkillProgressDTO

FSM_CONTEXT_KEY = "session_context"

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

    Рекурсивно обрабатывает как одиночные объекты, так и списки объектов.
    Если `value` не является Pydantic моделью, возвращает его без изменений.

    Args:
        value: Pydantic модель, список моделей или любые другие данные.

    Returns:
        Сериализованные данные (словарь, список словарей) или исходное значение.
    """
    if isinstance(value, BaseModel):
        log.debug(f"DtoHelper | action=serialize_model type='{type(value).__name__}'")
        return value.model_dump(mode="json")
    elif isinstance(value, list) and value and isinstance(value[0], BaseModel):
        log.debug(f"DtoHelper | action=serialize_list_of_models count={len(value)} type='{type(value[0]).__name__}'")
        return [v.model_dump(mode="json") for v in value]
    else:
        log.debug(f"DtoHelper | action=no_serialization_needed type='{type(value).__name__}'")
        return value


async def fsm_load_auto(state: FSMContext, key: str) -> Any:
    """
    Автоматически загружает и десериализует данные из FSM в Pydantic модели.

    Использует `DTO_MAP` для определения, в какой класс DTO нужно
    преобразовать данные, хранящиеся по указанному ключу.

    Args:
        state: Контекст FSM.
        key: Ключ, по которому хранятся данные в FSM.

    Returns:
        Pydantic модель, список моделей или исходные данные, если
        преобразование не требуется или невозможно.
    """
    log.debug(f"DtoHelper | action=load_auto_deserialize key='{key}'")
    data = await state.get_data()
    value = data.get(key)

    if value is None:
        log.debug(f"DtoHelper | status=not_found key='{key}' in FSM")
        return None

    return await fsm_converter(value, key)


async def fsm_converter(value: Any, key: str) -> Any:
    """
    Преобразует сырые данные (словарь/список) в Pydantic модель или список моделей.

    Args:
        value: Сырые данные (обычно `dict` или `list[dict]`).
        key: Ключ для поиска соответствующего класса DTO в `DTO_MAP`.

    Returns:
        Экземпляр Pydantic модели, список моделей или исходное значение.
    """
    dto_class = DTO_MAP.get(key)

    if not dto_class:
        log.debug(f"DtoHelper | reason='No DTO mapping' key='{key}' returning_raw_value")
        return value

    try:
        if isinstance(value, list):
            log.debug(f"DtoHelper | action=deserialize_list key='{key}' to_type='{dto_class.__name__}'")
            return [dto_class.model_validate(v) if isinstance(v, dict) else v for v in value]
        elif isinstance(value, dict):
            log.debug(f"DtoHelper | action=deserialize_dict key='{key}' to_type='{dto_class.__name__}'")
            return dto_class.model_validate(value)
        else:
            log.warning(
                f"DtoHelper | reason='Unexpected value type' key='{key}' type='{type(value).__name__}' returning_raw_value"
            )
            return value
    except (ValidationError, TypeError) as e:
        log.exception(f"DtoHelper | status=failed reason='Pydantic validation error' key='{key}' error='{e}'")
        return value


async def fsm_clean_core_state(state: FSMContext, event_source: CallbackQuery | Message) -> None:
    """
    Очищает FSM, сохраняя только "ядро" состояния (`SessionDataDTO`).

    Выполняет миграцию плоских ключей в контейнер `SessionDataDTO` при первом вызове.
    Если `user_id` отсутствует в контейнере, он извлекается из `event_source`.

    Args:
        state: Контекст FSM.
        event_source: Объект `CallbackQuery` или `Message`, из которого
                      можно извлечь `user_id` в случае необходимости.

    Raises:
        Exception: В случае критической ошибки во время очистки или миграции FSM.
    """
    log.debug("DtoHelper | action=fsm_clean_core_state_started")

    try:
        old_data = await state.get_data()
        clean_data = {}

        if FSM_CONTEXT_KEY in old_data:
            clean_data[FSM_CONTEXT_KEY] = old_data[FSM_CONTEXT_KEY]
            log.debug("DtoHelper | event=session_context_found_in_fsm")
        else:
            log.warning("DtoHelper | event=session_context_not_found_in_fsm action=migrating_old_keys")
            core_keys = SessionDataDTO.model_fields.keys()
            migrated_fields = {key: old_data.get(key) for key in core_keys}
            core_dto = SessionDataDTO(**migrated_fields)
            clean_data[FSM_CONTEXT_KEY] = await fsm_store(core_dto)

        if not clean_data.get(FSM_CONTEXT_KEY, {}).get("user_id") and event_source and event_source.from_user:
            migrated_dto = await fsm_converter(clean_data[FSM_CONTEXT_KEY], FSM_CONTEXT_KEY)
            if isinstance(migrated_dto, SessionDataDTO):
                migrated_dto.user_id = event_source.from_user.id
                clean_data[FSM_CONTEXT_KEY] = await fsm_store(migrated_dto)
                log.debug(f"DtoHelper | event=user_id_added_from_event_source user_id={event_source.from_user.id}")
            else:
                log.error("DtoHelper | status=failed reason='Migration failed, cannot get DTO from container'")

        await state.set_data(clean_data)
        log.info("DtoHelper | status=fsm_core_state_cleaned")

    except Exception:
        log.exception("DtoHelper | status=failed reason='Critical error during fsm_clean_core_state'")
        raise
