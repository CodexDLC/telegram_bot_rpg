# app/services/helpers_module/dto_helper.py
from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from pydantic import BaseModel, ValidationError

from app.resources.schemas_dto.character_dto import CharacterReadDTO, CharacterStatsReadDTO
from app.resources.schemas_dto.skill import SkillProgressDTO

FSM_CORE_KEYS = ["user_id", "char_id", "message_menu", "message_content"]


# Карта для сопоставления ключей FSM с классами DTO.
# Это позволяет автоматически восстанавливать Pydantic модели из словарей.
DTO_MAP: dict[str, type[BaseModel]] = {
    "character": CharacterReadDTO,
    "characters": CharacterReadDTO,  # Используется для списков
    "character_stats": CharacterStatsReadDTO,
    "character_progress": SkillProgressDTO,
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
    Очищает FSM, сохраняя "ядро" состояния.

    Эта функция-хелпер:
    1. Получает текущие данные из FSM.
    2. Создает новый, чистый словарь.
    3. Переносит в него *только* ключи из 'FSM_CORE_KEYS' (белый список).
    4. Пытается взять 'user_id' из 'event_source', если он отсутствует в FSM.
    5. Полностью перезаписывает состояние FSM (`set_data`).

    ВАЖНО: Эта функция НЕ меняет FSM-стейт (не вызывает set_state).
    За смену стейта отвечает вызвавший ее хэндлер.

    Args:
        state (FSMContext): Текущий FSM-контекст.
        event_source (Union[CallbackQuery, Message]): Событие (call или m),
            вызвавшее переход, для фоллбэка 'user_id'.

    Raises:
        Exception: Пробрасывает любую ошибку, возникшую в процессе,
                   чтобы хэндлер мог ее поймать (например, для ERR.generic_error).
    """
    log.debug("Запуск 'fsm_clean_core_state' для очистки FSM...")

    try:
        # 1. Получаем старые данные
        old_data = await state.get_data()
        log.debug(f"Полный state_data перед очисткой: {old_data}")

        clean_data = {}

        # 2. Собираем "чистый" словарь по "белому списку"
        for key in FSM_CORE_KEYS:
            if key in old_data:
                clean_data[key] = old_data[key]
            else:
                # Логируем, если важный ключ не найден
                log.warning(f"fsm_clean_core_state: Ключ ядра '{key}' не найден в FSM state.")

        # 3. Дополнительная логика (фоллбэк user_id, как ты и предлагал)
        if "user_id" not in clean_data:
            if event_source and event_source.from_user:
                clean_data["user_id"] = event_source.from_user.id
                log.debug("fsm_clean_core_state: 'user_id' добавлен из 'event_source'.")
            else:
                log.error("fsm_clean_core_state: 'user_id' не найден ни в FSM, ни в 'event_source'!")

        # 4. Важная проверка на char_id
        if "char_id" not in clean_data:
            log.error("fsm_clean_core_state: 'char_id' отсутствует в данных для перехода!")

        log.debug(f"Очищенный state_data для установки: {clean_data}")

        # 5. Полностью ПЕРЕЗАПИСЫВАЕМ стейт (как ты и просил)
        await state.set_data(clean_data)

        log.info("FSM state успешно очищен (сохранено только 'ядро').")

    except Exception as e:
        log.exception(f"Критическая ошибка во время 'fsm_clean_core_state': {e}")
        # Пробрасываем ошибку, чтобы хэндлер мог ее поймать
        raise
