# app/services/game_service/world/game_world_service.py
import json
from typing import Any

from loguru import logger as log

from apps.common.services.core_service.manager.world_manager import WorldManager


class GameWorldService:
    """
    Сервис игрового мира. Отвечает за бизнес-логику и валидацию данных,
    полученных от WorldManager (слой доступа к данным).
    """

    def __init__(self, world_manager: WorldManager):
        self.world_manager = world_manager

    # --- Private Helpers ---

    async def _get_raw_data(self, loc_id: str) -> dict[str, str] | None:
        """
        Приватный метод: читает сырые данные из Redis.
        """
        raw_data = await self.world_manager.get_location_meta(loc_id)
        if not raw_data:
            log.warning(f"GameWorldService | status=failed reason='Location not found' loc_id={loc_id}")
            return None
        return raw_data

    def _parse_json_fields(self, loc_id: str, raw_data: dict[str, str]) -> dict[str, Any] | None:
        """
        Приватный метод: парсит JSON-поля и собирает полный словарь.
        """
        try:
            exits = json.loads(raw_data.get("exits", "{}"))
            flags = json.loads(raw_data.get("flags", "{}"))
            tags = json.loads(raw_data.get("tags", "[]"))

            return {
                "name": raw_data.get("name"),
                "description": raw_data.get("description"),
                "exits": exits,
                "flags": flags,
                "tags": tags,
                "service": raw_data.get("service"),
                "zone_id": raw_data.get("zone_id"),
                "terrain": raw_data.get("terrain"),
            }
        except json.JSONDecodeError as e:
            log.error(f"GameWorldService | status=critical reason='Corrupted JSON' loc_id={loc_id} error={e}")
            return None
        except Exception as e:  # noqa: BLE001
            log.error(f"GameWorldService | status=error reason='Parse error' loc_id={loc_id} error={e}")
            return None

    # --- Public API ---

    async def get_location_for_navigation(self, loc_id: str) -> dict[str, Any] | None:
        """
        Возвращает полные данные локации (для навигации и отображения).
        Сохраняет старое название для совместимости.
        """
        raw_data = await self._get_raw_data(loc_id)
        if not raw_data:
            return None
        return self._parse_json_fields(loc_id, raw_data)

    async def get_location_encounter_params(self, loc_id: str) -> dict[str, Any] | None:
        """
        Возвращает только параметры для энкаунтеров (Tier, Biome, Tags).
        """
        # Можно оптимизировать: читать только нужные поля из Redis (HMGET),
        # но пока используем общий метод для простоты.
        data = await self.get_location_for_navigation(loc_id)
        if not data:
            return None

        flags = data.get("flags", {})

        return {
            "tier": int(flags.get("threat_tier", 1)),
            "biome": data.get("terrain", "wasteland"),
            "tags": data.get("tags", []),
        }
