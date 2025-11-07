# app/services/helpers_module/DTO_helper.py
import logging
from typing import Any, List, Dict, Type, Union
from aiogram.fsm.context import FSMContext
from pydantic import BaseModel

from app.resources.schemas_dto.character_dto import CharacterReadDTO, CharacterStatsReadDTO
from app.resources.schemas_dto.skill import SkillProgressDTO

log = logging.getLogger(__name__)

# Карта для сопоставления ключей FSM с классами DTO.
# Это позволяет автоматически восстанавливать Pydantic модели из словарей.
DTO_MAP: Dict[str, Type[BaseModel]] = {
    "character": CharacterReadDTO,
    "characters": CharacterReadDTO,  # Используется для списков
    "character_stats": CharacterStatsReadDTO,
    "character_progress": SkillProgressDTO,
}
log.debug(f"Карта DTO_MAP инициализирована с {len(DTO_MAP)} записями.")


async def fsm_store(value: Any) -> Union[Dict, List[Dict], Any]:
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
        return value.model_dump(mode='json')
    elif isinstance(value, list) and value and isinstance(value[0], BaseModel):
        log.debug(f"Сериализация списка из {len(value)} Pydantic моделей '{type(value[0]).__name__}'.")
        return [v.model_dump(mode='json') for v in value]
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
            log.warning(f"Ожидался dict или list для ключа '{key}', но получен '{type(value).__name__}'. Преобразование невозможно.")
            return value
    except Exception as e:
        log.exception(f"Ошибка валидации Pydantic при преобразовании данных для ключа '{key}': {e}")
        # В случае ошибки возвращаем исходное значение, чтобы не сломать логику.
        return value
