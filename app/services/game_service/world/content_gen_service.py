import asyncio
import json

from loguru import logger as log

from app.services.gemini_service.gemini_service import gemini_answer
from database.repositories import IWorldRepo


class ContentGenerationService:
    def __init__(self, world_repo: IWorldRepo):
        self.repo = world_repo
        self.batch_size = 5  # Размер пачки для ЛЛМ
        self.semaphore = asyncio.Semaphore(2)

    async def generate_content_for_path(self, path_coords: list[tuple[int, int]]):
        """
        Генерирует описания для списка координат (пути).
        """
        log.info(f"ContentGen | task=started nodes={len(path_coords)}")

        # Разбиваем на батчи
        chunks = [path_coords[i : i + self.batch_size] for i in range(0, len(path_coords), self.batch_size)]

        tasks = []
        for chunk in chunks:
            tasks.append(self._process_batch(chunk))

        await asyncio.gather(*tasks)
        log.info("ContentGen | task=finished")

    async def _process_batch(self, chunk: list[tuple[int, int]]):
        async with self.semaphore:
            payload = []

            # 1. СБОР КОНТЕКСТА (Enrichment)
            for x, y in chunk:
                # Берем саму ноду
                node = await self.repo.get_node(x, y)
                if not node:
                    continue

                # Берем её теги (это база)
                my_tags = node.flags.get("biome_tags", [])

                # Собираем соседей (Surroundings)
                surroundings = await self._get_surroundings_context(x, y)

                # Формируем объект для ЛЛМ
                item = {
                    "id": f"{x}_{y}",
                    "internal_tags": my_tags,  # "Кто я?" (Лес, Дорога)
                    "surroundings": surroundings,  # "Кто вокруг?" (Север: Ворота, Юг: Болото)
                    "fill_content": {  # "Что заполнить?"
                        "title": "",
                        "description": "",
                    },
                }
                payload.append(item)

            if not payload:
                return

            # 2. ЗАПРОС К GEMINI
            try:
                response_text = await gemini_answer(
                    mode="batch_location_desc", user_text=json.dumps(payload, ensure_ascii=False)
                )

                # Чистка JSON (иногда нейронка пишет ```json)
                clean_json = response_text.replace("```json", "").replace("```", "").strip()
                result_map = json.loads(clean_json)  # Ожидаем { "x_y": {title, desc} }

            except json.JSONDecodeError as e:
                log.error(f"ContentGen | llm_error chunk={chunk[0]} err={e}")
                return

            # 3. СОХРАНЕНИЕ
            for loc_id, content in result_map.items():
                try:
                    x, y = map(int, loc_id.split("_"))

                    # Находим исходные теги, чтобы сохранить их в content
                    # (Мы обязаны хранить их вместе с текстом для UI)
                    original_item = next((i for i in payload if i["id"] == loc_id), None)
                    tags = original_item["internal_tags"] if original_item else []

                    final_content = {
                        "title": content.get("title", "Пустошь"),
                        "description": content.get("description", "..."),
                        "environment_tags": tags,  # Важно!
                    }

                    # Обновляем ТОЛЬКО поле content (is_active и флаги не трогаем)
                    # Используем create_or_update_node, он смерджит это.
                    # Но лучше бы иметь метод update_content.
                    # Пока используем универсальный:

                    # Нам нужно прочитать сектор ID, чтобы вызвать update (костыль ORM)
                    # Или передать любой, repo сам разберется (если мы не меняем PK).
                    # Но лучше передать правильный или игнорируемый.

                    # ВНИМАНИЕ: Тут мы полагаемся на то, что нода УЖЕ ЕСТЬ (создана скриптом).
                    # Поэтому repo.create_or_update_node сработает как UPDATE.

                    # Получаем sector_id (он обязателен для модели, хоть и не меняется)
                    node_db = await self.repo.get_node(x, y)
                    sec_id = node_db.sector_id if node_db else "D4"

                    await self.repo.create_or_update_node(
                        x=x,
                        y=y,
                        sector_id=sec_id,
                        content=final_content,
                        is_active=True,  # Подтверждаем активность
                    )

                except (ValueError, KeyError) as e:
                    log.error(f"ContentGen | save_error id={loc_id} err={e}")

    async def _get_surroundings_context(self, x: int, y: int) -> dict[str, list[str]]:
        """
        Читает теги соседей из БД.
        """
        directions = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
        result = {}

        for dir_name, (dx, dy) in directions.items():
            nx, ny = x + dx, y + dy
            node = await self.repo.get_node(nx, ny)

            if node:
                # Если сосед активен или имеет теги (даже в тумане)
                tags = node.flags.get("biome_tags", [])
                if node.flags.get("is_safe_zone"):
                    tags.append("safe_zone")

                if tags:
                    result[dir_name] = tags
            else:
                result[dir_name] = ["void"]  # Край карты

        return result
