# app/services/game_service/world/game_world_service.py (Финальная версия с логикой)
import json
from typing import Any

from loguru import logger as log

from apps.common.services.core_service.manager.world_manager import WorldManager

# Мы предполагаем, что WorldManager имеет метод для чтения данных из Redis, например:
# async def get_location_hash(self, loc_id: str) -> Dict[str, str] | None:


class GameWorldService:
    """
    Сервис игрового мира. Отвечает за бизнес-логику и валидацию данных,
    полученных от WorldManager (слой доступа к данным).
    """

    def __init__(self, world_manager: WorldManager):
        self.world_manager = world_manager

    async def get_location_for_navigation(self, loc_id: str) -> dict[str, Any] | None:
        """
        Получает данные локации, проводя необходимые проверки для навигации.
        """
        # 1. Получаем "сырые" данные (hash) из WorldManager (который идет в Redis)
        raw_data = await self.world_manager.get_location_meta(loc_id)

        if not raw_data:
            log.warning(f"GameWorldService | status=failed reason='Location not found in Redis' loc_id={loc_id}")
            return None

        # 2. 🔥 Валидация и защита от падения (ваша логика!)
        try:
            # Преобразуем JSON-строки, которые WorldLoaderService записал в Redis, обратно в dict
            # Нам нужны: exits, flags, tags, name, description
            exits = json.loads(raw_data.get("exits", "{}"))
            flags = json.loads(raw_data.get("flags", "{}"))
            # ... и т.д. для других полей, которые были записаны в виде JSON.

            # 3. Собираем чистый DTO/Dict для NavigationService
            return {
                "name": raw_data.get("name"),
                "description": raw_data.get("description"),
                "exits": exits,
                "flags": flags,
                # ... другие нужные поля
            }

        except json.JSONDecodeError as e:
            log.error(
                f"GameWorldService | status=critical reason='Corrupted JSON data in Redis' loc_id={loc_id} error={e}"
            )
            return None  # Защита от падения при поврежденных данных
        except (TypeError, KeyError) as e:
            log.error(
                f"GameWorldService | status=error reason='Unexpected error during location data processing' loc_id={loc_id} error={e}"
            )
            return None
