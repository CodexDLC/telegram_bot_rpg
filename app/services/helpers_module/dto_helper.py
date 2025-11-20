# app/services/helpers_module/dto_helper.py
from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from pydantic import BaseModel, ValidationError

from app.resources.schemas_dto.character_dto import CharacterReadDTO, CharacterStatsReadDTO
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
from app.resources.schemas_dto.skill import SkillProgressDTO

FSM_CONTEXT_KEY = "session_context"

# Карта для сопоставления ключей FSM с классами DTO.
# Это позволяет автоматически восстанавливать Pydantic модели из словарей.
DTO_MAP: dict[str, type[BaseModel]] = {
    "character": CharacterReadDTO,
    "characters": CharacterReadDTO,  # Используется для списков
    "character_stats": CharacterStatsReadDTO,
    "character_progress": SkillProgressDTO,
    FSM_CONTEXT_KEY: SessionDataDTO,
}
log.debug(f"Карта DTO_MAP инициализирована с {len(DTO_MAP)} записями.")


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
        log.debug(f"Сериализация Pydantic модели '{type(value).__name__}' в словарь.")
        return value.model_dump(mode="json")
    elif isinstance(value, list) and value and isinstance(value[0], BaseModel):
        log.debug(f"Сериализация списка из {len(value)} Pydantic моделей '{type(value[0]).__name__}'.")
        return [v.model_dump(mode="json") for v in value]
    else:
        log.debug(f"Значение типа '{type(value).__name__}' не требует сериализации.")
        return value


async def fsm_load_auto(state: FSMContext, key: str) -> Any:
    """
    Автоматически загружает и десериализует данные из FSM в Pydantic модели.

    Использует `DTO_MAP` для определения, в какой класс DTO нужно
    преобразовать данные, хранящиеся по указанному ключу.

    Args:
        state (FSMContext): Контекст FSM.
        key (str): Ключ, по которому хранятся данные.

    Returns:
        Pydantic модель, список моделей или исходные данные, если
        преобразование не требуется или невозможно.
    """
    log.debug(f"Загрузка и автоматическая десериализация данных по ключу FSM: '{key}'.")
    data = await state.get_data()
    value = data.get(key)

    if value is None:
        log.debug(f"Данные по ключу '{key}' в FSM не найдены.")
        return None

    return await fsm_convector(value, key)


async def fsm_convector(value: Any, key: str) -> Any:
    """
    Преобразует сырые данные (словарь/список) в Pydantic модель.

    Вспомогательная функция, которая выполняет фактическое преобразование,
    используя `DTO_MAP`.

    Args:
        value: Сырые данные (обычно `dict` или `list[dict]`).
        key (str): Ключ для поиска соответствующего класса DTO в `DTO_MAP`.

    Returns:
        Экземпляр Pydantic модели, список моделей или исходное значение.
    """
    dto_class = DTO_MAP.get(key)

    if not dto_class:
        log.debug(f"Для ключа '{key}' не найдено сопоставление в DTO_MAP. Возвращается исходное значение.")
        return value

    try:
        if isinstance(value, list):
            log.debug(f"Десериализация списка по ключу '{key}' в список моделей '{dto_class.__name__}'.")
            return [dto_class.model_validate(v) if isinstance(v, dict) else v for v in value]
        elif isinstance(value, dict):
            log.debug(f"Десериализация словаря по ключу '{key}' в модель '{dto_class.__name__}'.")
            return dto_class.model_validate(value)
        else:
            log.warning(
                f"Ожидался dict или list для ключа '{key}', но получен '{type(value).__name__}'. Преобразование невозможно."
            )
            return value
    except (ValidationError, TypeError) as e:
        log.exception(f"Ошибка валидации Pydantic при преобразовании данных для ключа '{key}': {e}")
        # В случае ошибки возвращаем исходное значение, чтобы не сломать логику.
        return value


async def fsm_clean_core_state(state: FSMContext, event_source: CallbackQuery | Message) -> None:
    """
    Очищает FSM, сохраняя "ядро" состояния (SessionDataDTO).
    Выполняет миграцию плоских ключей в контейнер при первом вызове.
    """
    log.debug("Запуск 'fsm_clean_core_state' для очистки FSM...")

    try:
        old_data = await state.get_data()
        clean_data = {}

        # 1. Проверяем, существует ли уже новый контейнер FSM_CONTEXT_KEY.
        if FSM_CONTEXT_KEY in old_data:
            # СЛУЧАЙ 1: Контейнер уже создан. Просто сохраняем его.
            clean_data[FSM_CONTEXT_KEY] = old_data[FSM_CONTEXT_KEY]
            log.debug("Контейнер 'session_context' найден, сохраняется без изменений.")
        else:
            # СЛУЧАЙ 2: Миграция. Собираем DTO из старых плоских ключей.
            log.warning("Контейнер 'session_context' не найден. Выполняется миграция старых ключей.")

            # ВАЖНО: Мы должны использовать имена полей из SessionDataDTO.
            core_keys = SessionDataDTO.model_fields.keys()
            migrated_fields = {key: old_data.get(key) for key in core_keys}

            # Создаем DTO (Pydantic сам обработает Optional и проверит типы)
            core_dto = SessionDataDTO(**migrated_fields)

            # Сохраняем DTO как словарь (сериализуем) под новым ключом.
            clean_data[FSM_CONTEXT_KEY] = await fsm_store(core_dto)

        # 2. Обработка фоллбэка user_id, если он не был найден в DTO
        if not clean_data.get(FSM_CONTEXT_KEY, {}).get("user_id") and event_source and event_source.from_user:
            # ВАЖНО: Мы не можем напрямую писать в словарь, который может быть DTO.
            # Мы должны его прочитать, изменить и записать обратно.

            # Читаем DTO из словаря (десериализуем)
            migrated_dto = await fsm_convector(clean_data[FSM_CONTEXT_KEY], FSM_CONTEXT_KEY)
            if isinstance(migrated_dto, SessionDataDTO):
                migrated_dto.user_id = event_source.from_user.id
                # Записываем обратно как словарь (сериализуем)
                clean_data[FSM_CONTEXT_KEY] = await fsm_store(migrated_dto)
                log.debug(f"User ID {event_source.from_user.id} добавлен в контейнер из event_source.")
            else:
                log.error("Миграция провалилась, не могу получить DTO из контейнера.")

        # 3. Полностью ПЕРЕЗАПИСЫВАЕМ стейт (удаляя все временные поля)
        await state.set_data(clean_data)
        log.info("FSM state успешно очищен (сохранен только контейнер 'session_context').")

    except Exception as e:
        log.exception(f"Критическая ошибка во время 'fsm_clean_core_state': {e}")
        # Пробрасываем ошибку, чтобы хэндлер мог ее поймать
        raise
