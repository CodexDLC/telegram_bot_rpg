# app/services/helpers_module/get_data_handlers/status_data_helper.py
from typing import Any

from loguru import logger as log

from app.services.helpers_module.data_loader_service import load_data_auto
from app.services.helpers_module.dto_helper import fsm_store


async def get_status_data_package(char_id: int, user_id: int) -> dict[str, Any] | None:
    """
    Загружает и упаковывает единый пакет данных для меню статуса персонажа.

    Эта функция-хелпер асинхронно загружает все необходимые данные
    (основная информация, характеристики, прогресс навыков) для указанного
    персонажа, используя `load_data_auto`. Затем она сериализует
    полученные DTO в словари, готовые для хранения в FSM.

    Args:
        char_id (int): ID персонажа, для которого загружаются данные.
        user_id (int): ID пользователя, для валидации и передачи в загрузчик.

    Returns:
        Optional[Dict[str, Any]]: Словарь с упакованными и сериализованными
                                  данными, если загрузка прошла успешно.
                                  Ключи: 'id', 'character', 'character_stats',
                                  'character_progress_skill'.
                                  Возвращает None, если данные не были загружены.
    """
    log.info(f"Запрос на загрузку полного пакета данных о статусе для char_id={char_id}, user_id={user_id}")

    # Определяем, какие данные нам нужны.
    required_data = ["character", "character_stats", "character_progress"]

    # Выполняем параллельную загрузку.
    loaded_data = await load_data_auto(include=required_data, character_id=char_id, user_id=user_id)

    # Проверяем, что все необходимые данные были успешно загружены.
    if not all(key in loaded_data and loaded_data[key] is not None for key in required_data):
        log.warning(
            f"Не удалось загрузить полный пакет данных для char_id={char_id}. Получено: {list(loaded_data.keys())}"
        )
        return None

    log.debug(f"Данные для char_id={char_id} успешно загружены. Начало упаковки и сериализации.")

    # Сериализуем DTO в словари для хранения в FSM.
    packaged_data = {
        "id": char_id,
        "character": await fsm_store(value=loaded_data.get("character")),
        "character_stats": await fsm_store(value=loaded_data.get("character_stats")),
        "character_progress_skill": await fsm_store(value=loaded_data.get("character_progress")),
    }

    log.info(f"Пакет данных для char_id={char_id} успешно сформирован.")
    log.debug(f"Содержимое пакета: {packaged_data}")
    return packaged_data
