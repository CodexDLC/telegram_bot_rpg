# (Подсказка)
import logging
from app.services.helpers_module.data_loader_service import load_data_auto
from app.services.helpers_module.DTO_helper import fsm_store

log = logging.getLogger(__name__)

async def get_status_data_package(
    char_id: int,
    user_id: int
) -> dict[str, int | dict | list[dict]] | None:
    """
    (Бывший get_bd_data_staus)
    Загружает ЕДИНЫЙ пакет данных ('character', 'character_stats', 'character_progress')
    для меню статуса.
    """
    log.info(f"Загрузка пакета данных о статусе для char_id={char_id}")

    get_data = await load_data_auto(
        ["character", "character_stats", "character_progress"],
        character_id=char_id,
        user_id=user_id
    )

    if get_data:
        bd_data_by_save = {
            "id": char_id,
            "character": await fsm_store(value=get_data.get("character")),
            "character_stats": await fsm_store(value=get_data.get("character_stats")),
            "character_progress_skill": await fsm_store(value=get_data.get("character_progress"))
        }
        return bd_data_by_save
    else:
        log.warning(f"Не удалось загрузить данные для char_id={char_id}")
        return None