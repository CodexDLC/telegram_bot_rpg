from abc import ABC, abstractmethod
from typing import Any

from apps.common.database.model_orm.world import WorldGrid, WorldRegion


class IWorldRepo(ABC):
    """
    Интерфейс для работы с картой мира (Регионы и Сетка).
    Обеспечивает низкоуровневый доступ к таблицам world_regions и world_grid.
    """

    # --- РЕГИОНЫ (Regions / Sectors) ---

    @abstractmethod
    async def upsert_region(self, region_data: WorldRegion) -> None:
        """
        Создает или обновляет запись о Регионе (15x15).
        Используется при генерации макро-структуры мира.
        """
        pass

    @abstractmethod
    async def get_region(self, region_id: str) -> WorldRegion | None:
        """
        Получает данные региона по ID (например, 'D4').
        Нужно, чтобы прочитать карту под-зон (sector_map).
        """
        pass

    # --- КЛЕТКИ (Nodes / Grid) ---

    @abstractmethod
    async def get_node(self, x: int, y: int) -> WorldGrid | None:
        """
        Получает одну клетку по координатам.
        Используется для проверки состояния и получения тегов перед генерацией.
        """
        pass

    @abstractmethod
    async def create_or_update_node(
        self,
        x: int,
        y: int,
        sector_id: str,
        is_active: bool = False,
        flags: dict | None = None,
        content: dict | None = None,
        service_object_key: str | None = None,
    ) -> None:
        """
        Полная запись клетки (UPSERT).
        Используется генератором (Seeding) для создания мира или перезаписи статикой.
        Если клетка существует — обновляет все переданные поля.
        """
        pass

    @abstractmethod
    async def update_flags(self, x: int, y: int, new_flags: dict[str, Any], activate_node: bool = False) -> bool:
        """
        Точечное обновление JSON-поля `flags`.

        Логика: Читает текущие флаги -> Мерджит с new_flags -> Сохраняет.
        Используется для механик (прокладка дорог, изменение уровня угрозы),
        не затрагивая контент.

        Args:
            activate_node: Если True, дополнительно ставит is_active=True.
        """
        pass

    @abstractmethod
    async def update_content(self, x: int, y: int, new_content: dict[str, Any]) -> bool:
        """
        Точечное обновление JSON-поля `content`.

        Используется сервисом генерации (LLM) для записи текстов и тегов,
        не затрагивая флаги механики.
        """
        pass

    @abstractmethod
    async def get_active_nodes(self) -> list[WorldGrid]:
        """
        Возвращает список ВСЕХ активных клеток (is_active=True).
        Используется Runtime-сервисом при старте сервера для загрузки в Redis.
        """
        pass

    @abstractmethod
    async def get_nodes_in_rect(self, x_start: int, y_start: int, width: int, height: int) -> list[WorldGrid]:
        """
        Возвращает все клетки в указанном прямоугольнике одним запросом.
        Нужен для ZoneOrchestrator.
        """
        pass
