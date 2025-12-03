import json

from loguru import logger as log

from app.resources.game_data.graf_data_world.start_vilage import WORLD_DATA
from app.services.core_service.manager.world_manager import WorldManager


class GameWorldService:
    """
    Сервис бизнес-логики для управления игровым миром.

    Отвечает за инициализацию мира из статических ресурсов,
    предоставление данных о локациях и управление игроками в локациях.
    """

    def __init__(self, world_manager: WorldManager):
        """
        Инициализирует GameWorldService.

        Args:
            world_manager: Менеджер игрового мира.
        """
        self.world_manager = world_manager
        log.debug("GameWorldService | status=initialized")

    async def initialize_world_locations(self) -> None:
        """
        Загружает данные о мировых локациях из `WORLD_DATA` в Redis.

        Этот метод вызывается один раз при старте приложения для инициализации
        или проверки наличия данных о мире в Redis. Данные форматируются
        для хранения в хешах Redis.
        """
        log.info("WorldInit | event=start")
        locations_loaded = 0

        for loc_id, loc_data in WORLD_DATA.items():
            data_to_write = {
                "name": loc_data.get("title"),
                "description": loc_data.get("description"),
                "exits": json.dumps(loc_data.get("exits", {})),
                "tags": json.dumps(loc_data.get("environment_tags", [])),
            }
            await self.world_manager.write_location_meta(loc_id, data_to_write)
            locations_loaded += 1
            log.debug(f"WorldInit | status=loaded loc_id='{loc_id}' name='{loc_data.get('title')}'")

        log.info(f"WorldInit | status=finished loaded_count={locations_loaded}")

    async def add_npc_to_location(self, npc_id: int, loc_id: str) -> None:
        """
        Динамически "спавнит" NPC в указанной мировой локации.

        Записывает ID NPC в специальное поле 'npc_list' в хеше локации.

        Args:
            npc_id: Идентификатор NPC из "холодной" SQL базы.
            loc_id: Идентификатор локации, где появляется NPC.
        """
        # TODO: Реализовать логику добавления NPC в локацию.
        # 1. Прочитать текущий 'npc_list' из хеша локации.
        # 2. Десериализовать JSON-список, добавить npc_id, сериализовать обратно.
        # 3. Обновить хеш локации через `world_manager.write_location_meta`.
        log.warning(
            f"WorldService | action=add_npc_to_location status=not_implemented npc_id={npc_id} loc_id='{loc_id}'"
        )
        pass

    async def get_location_for_navigation(self, loc_id: str) -> dict | None:
        """
        Получает данные о локации, отформатированные для отображения игроку в навигации.

        Десериализует JSON-поля (exits, tags) обратно в Python-объекты.

        Args:
            loc_id: Уникальный идентификатор локации.

        Returns:
            Словарь с данными локации, готовыми для навигации, или None, если локация не найдена
            или произошла ошибка десериализации.
        """
        raw_data = await self.world_manager.get_location_meta(loc_id)

        if not raw_data:
            log.warning(f"WorldService | status=failed reason='Meta data not found' loc_id='{loc_id}'")
            return None

        navigation_data = {}
        try:
            navigation_data["name"] = raw_data.get("name", "Без Имени")
            navigation_data["description"] = raw_data.get("description", "...")
            navigation_data["exits"] = json.loads(raw_data.get("exits", "{}"))
            navigation_data["tags"] = json.loads(raw_data.get("tags", "[]"))
            return navigation_data
        except json.JSONDecodeError:
            log.error(f"WorldService | status=failed reason='JSON decode error' loc_id='{loc_id}'", exc_info=True)
            return None
