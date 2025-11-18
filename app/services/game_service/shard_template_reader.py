# app/services/game_service/shard_template_reader.py
from typing import Any

from loguru import logger as log


class ShardTemplateReader:
    """
    Предоставляет удобный интерфейс для чтения данных из шаблона подземелья.

    Этот класс инкапсулирует логику доступа к различным частям
    словаря-шаблона, предоставляя типизированные методы для получения
    информации о комнатах, их свойствах и метаданных подземелья.
    """

    def __init__(self, dungeon_template: dict):
        """
        Инициализирует ридер с заданным шаблоном подземелья.

        Args:
            dungeon_template: Словарь, содержащий полную структуру шаблона подземелья.
        """
        # "Запоминаем" переданный шаблон для последующего использования.
        self.template = dungeon_template

        # Логируем основную информацию о загруженном шаблоне для отладки.
        try:
            name = self.template.get("dungeon_meta", {}).get("name", "N/A")
            level = self.template.get("dunegon_meta", {}).get("level", "?")
            rooms_count = len(self.template.get("rooms", {}))

            log.debug(f"{self.__class__.__name__} initialized: Name='{name}', Level={level}, Rooms={rooms_count}")
        except (KeyError, TypeError) as e:
            # Если при логировании метаданных происходит ошибка, это не должно
            # прерывать выполнение. Просто выводим предупреждение.
            log.warning(f"Failed to log template metadata on init: {e}")

    def get_room_description(self, room_id: str) -> str:
        """
        Возвращает текстовое описание для указанной комнаты.

        Args:
            room_id: Уникальный идентификатор комнаты.

        Returns:
            Строка с описанием комнаты.
        """
        # Извлекаем данные из вложенной структуры словаря.
        data = self.template["rooms"][room_id]["description"]

        # Логируем действие для возможности отслеживания вызовов.
        log.debug(f"get_room_description(room_id={room_id}): Returning description (len={len(data)}).")

        # Возвращаем полученное описание.
        return data

    def get_room_name(self, room_id: str) -> str:
        """
        Возвращает название для указанной комнаты.

        Args:
            room_id: Уникальный идентификатор комнаты.

        Returns:
            Строка с названием комнаты.
        """
        data = self.template["rooms"][room_id]["name"]
        log.debug(f"get_room_name(room_id={room_id}): Returning name: '{data}'")
        return data

    def get_room_exits(self, room_id: str) -> dict[str, str]:
        """
        Возвращает словарь выходов из указанной комнаты.

        Args:
            room_id: Уникальный идентификатор комнаты.

        Returns:
            Словарь, где ключи - направления, а значения - ID комнат,
            в которые ведут эти выходы.
        """
        data = self.template["rooms"][room_id]["exits"]
        log.debug(f"get_room_exits(room_id={room_id}): Returning exits dict: {data}")
        return data

    def get_room_tags(self, room_id: str) -> list[str]:
        """
        Возвращает список тегов окружения для указанной комнаты.

        Args:
            room_id: Уникальный идентификатор комнаты.

        Returns:
            Список строк, представляющих теги.
        """
        data = self.template["rooms"][room_id]["environment_tags"]
        log.debug(f"get_room_tags(room_id={room_id}): Returning tags list: {data}")
        return data

    def get_meta_rooms(self) -> dict[str, str]:
        """
        Возвращает словарь "мета-комнат" из метаданных подземелья.

        Мета-комнаты - это специальные комнаты, такие как стартовая комната
        или комната с боссом.

        Returns:
            Словарь, где ключи - это тип мета-комнаты (e.g., 'start_room'),
            а значения - ID соответствующей комнаты.
        """
        data = self.template["dungeon_meta"]["meta_rooms"]
        log.debug(f"get_meta_rooms(): Returning meta_rooms dict: {data}")
        return data

    def get_room_data(self, room_id: str) -> dict[str, Any]:
        """
        Возвращает полный "сырой" словарь (dict) для указанной комнаты.

        Этот метод полезен, когда требуется доступ ко всем данным комнаты,
        а не к какому-то конкретному полю.

        Args:
            room_id: Уникальный идентификатор комнаты.

        Returns:
            Словарь со всеми данными, относящимися к комнате.
        """
        data = self.template["rooms"][room_id]
        log.debug(f"get_room_data(room_id={room_id}): Returning full room data dict.")
        return data
