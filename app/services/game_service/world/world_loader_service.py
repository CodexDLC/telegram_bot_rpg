import json
from typing import Any

from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError

from database.model_orm.world import WorldGrid
from database.repositories import get_world_repo
from database.session import get_async_session


class WorldLoaderService:
    """
    Сервис загрузки активной части мира (Active Grid) из SQL в кэш Redis.
    """

    def __init__(self, world_manager):
        self.world_manager = world_manager
        log.debug("WorldLoaderService | status=initialized")

    async def init_world_cache(self) -> int:
        """
        Читает все активные клетки (nodes) из SQL, рассчитывает выходы и загружает их в Redis.
        """
        log.info("WorldLoaderService | event=start_loading_active_nodes")

        async with get_async_session() as session:
            repo = get_world_repo(session)

            try:
                active_nodes = await repo.get_active_nodes()
            except SQLAlchemyError as e:
                log.exception(f"WorldLoaderService | status=failed reason='SQL fetch error' error='{e}'")
                return 0

            node_map: dict[str, WorldGrid] = {f"{node.x}_{node.y}": node for node in active_nodes}

            count = 0
            for node in active_nodes:
                loc_id = f"{node.x}_{node.y}"
                exits_data = self._calculate_exits_for_node(node, node_map)

                content_data: dict[str, Any] = node.content or {}
                flags_data: dict[str, Any] = node.flags or {}

                redis_data = {
                    "name": content_data.get("title", f"Узел {loc_id}"),
                    "description": content_data.get("description", "..."),
                    "exits": json.dumps(exits_data),
                    "tags": json.dumps(content_data.get("environment_tags", [])),
                    "service": node.service_object_key or "",
                    "flags": json.dumps(flags_data),
                }

                await self.world_manager.write_location_meta(loc_id, redis_data)
                count += 1

            log.info(f"WorldLoaderService | status=finished loaded_count={count}")
            return count

    def _calculate_exits_for_node(self, node: WorldGrid, node_map: dict[str, WorldGrid]) -> dict[str, Any]:
        """
        Рассчитывает доступные выходы, учитывая флаг 'restricted_exits'.
        """
        exits = {}
        directions = {
            "north": (0, -1),
            "south": (0, 1),
            "west": (-1, 0),
            "east": (1, 0),
        }

        current_flags = node.flags if isinstance(node.flags, dict) else {}
        restricted = current_flags.get("restricted_exits", [])

        if node.service_object_key:
            key = f"svc:{node.service_object_key}"
            content = node.content or {}
            title = content.get("title", "Сервис")
            exits[key] = {
                "desc_next_room": f"Войти в {title}",
                "time_duration": 1.0,
                "text_button": f"Войти в {title}",
            }

        for dir_name, (dx, dy) in directions.items():
            if dir_name in restricted:
                continue

            nx, ny = node.x + dx, node.y + dy
            neighbor_id = f"{nx}_{ny}"
            neighbor = node_map.get(neighbor_id)

            if neighbor and neighbor.is_active:
                content = neighbor.content or {}
                title = content.get("title") or f"Путь в {nx}:{ny}"

                # ИСПРАВЛЕНО: Гарантируем, что neighbor.flags - это словарь
                neighbor_flags = neighbor.flags if isinstance(neighbor.flags, dict) else {}
                has_road = neighbor_flags.get("has_road", False)
                time_duration = 2.0 if has_road else 4.0

                key = f"nav:{neighbor_id}"

                exits[key] = {
                    "desc_next_room": title,
                    "time_duration": time_duration,
                    "text_button": f"К {title}",
                }

        return exits
