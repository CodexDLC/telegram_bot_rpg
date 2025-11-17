# app/services/game_service/game_world_service.py
import json
from loguru import logger as log

# 1. Импортируем "глупый" Менеджер (Репозиторий)
from app.services.core_service.manager.world_manager import world_manager

# 2. Импортируем "сырые" данные о мире
from app.resources.game_data.graf_data_world.start_vilage import WORLD_DATA



class GameWorldService:
    """
    Сервис бизнес-логики для управления Миром.

    Отвечает за "умные" операции: инициализацию мира из ресурсов,
    динамическое добавление/удаление NPC, запуск мировых событий и т.д.
    Использует "глупый" WorldManager для фактической записи в Redis.
    """

    async def initialize_world_locations(self) -> None:
        """
        Загружает 'сырую' карту (WORLD_DATA) в Redis 'world:loc:*'.

        Вызывается один раз при старте бота (в main.py).
        Форматирует данные из Python-словаря в структуру для Хэша (Hash).
        """
        log.info("Запуск инициализации/проверки карты мира в Redis...")
        locations_loaded = 0

        # 1. Начать цикл (как ты и сказал)
        for loc_id, loc_data in WORLD_DATA.items():

            data_to_write = {
                "name": loc_data.get("title"),
                "description": loc_data.get("description"),
                "exits": json.dumps(loc_data.get("exits", {})),
                "tags": json.dumps(loc_data.get("environment_tags", []))
            }

            # 4. Вызвать "глупый" менеджер для записи
            await world_manager.write_location_meta(loc_id, data_to_write)
            locations_loaded += 1
            log.debug(f"Локация = {loc_data.get("title")} загружена в Redis.")

        log.info(f"Инициализация мира завершена. Загружено/проверено {locations_loaded} локаций.")


    async def add_npc_to_location(self, npc_id: int, loc_id: str) -> None:
        """
        (Твой план на будущее)
        Динамически "спавнит" NPC в мировой локации.

        Записывает ID NPC в специальное поле 'npc_list' в 'world:loc:<loc_id>'.
        (Это не Set, а просто поле в Хэше).

        Args:
            npc_id (int): ID NPC из "холодной" SQL базы.
            loc_id (str): ID локации, где он появляется.
        """
        # Твоя логика:
        # 1. (Сложная логика): Сначала прочитать 'npc_list' из Хэша
        # 2. (Сложная логика): Десериализовать JSON-список, добавить ID, сериализовать обратно
        # 3. Вызвать await world_manager
        pass

    async def get_location_for_navigation(self, loc_id: str) -> dict | None:
        """
        Получает данные локации, готовые для показа игроку.

        Десериализует JSON-поля (exits, tags) обратно в Python-объекты.
        """

        # 1. Получить "сырые" данные (dict[str, str])
        raw_data = await world_manager.get_location_meta(loc_id)

        if not raw_data:
            log.warning(f"Не найдены мета-данные для локации: {loc_id}")
            return None

        # 2. Создаем новый, "чистый" словарь для результата
        navigation_data = {}

        try:
            # 3. Копируем "простые" строковые поля как есть
            navigation_data["name"] = raw_data.get("name", "Без Имени")
            navigation_data["description"] = raw_data.get("description", "...")

            # 4. Десериализуем JSON-поля
            # (Используем "{}", "[]" как СТРОКИ по умолчанию)
            navigation_data["exits"] = json.loads(raw_data.get("exits", "{}"))
            navigation_data["tags"] = json.loads(raw_data.get("tags", "[]"))

            return navigation_data

        except json.JSONDecodeError as e:
            log.error(f"Критическая ошибка: не удалось распарсить JSON из Redis для loc_id={loc_id}. Ошибка: {e}")
            return None


# Создаем глобальный экземпляр (Singleton)
game_world_service = GameWorldService()