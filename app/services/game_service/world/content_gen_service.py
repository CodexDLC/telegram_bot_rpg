import asyncio
import json
import traceback  # 🔥 Добавлено для отладки

from loguru import logger as log

from app.services.gemini_service.gemini_service import gemini_answer
from database.repositories import IWorldRepo


class ContentGenerationService:
    def __init__(self, world_repo: IWorldRepo):
        self.repo = world_repo
        self.batch_size = 5

    async def generate_content_for_path(self, path_coords: list[tuple[int, int]]):
        """
        Генерирует описания последовательно, пачками по 5 штук.
        """
        total_nodes = len(path_coords)
        log.info(f"ContentGen | task=started nodes={total_nodes} batch_size={self.batch_size} mode=sequential")

        # Разбиваем на мелкие батчи
        chunks = [path_coords[i : i + self.batch_size] for i in range(0, total_nodes, self.batch_size)]

        log.info(f"ContentGen | action=batching total_batches={len(chunks)}")

        # 🔥 FIX: Строго последовательная обработка
        for i, chunk in enumerate(chunks):
            log.info(f"ContentGen | processing_batch {i + 1}/{len(chunks)}...")
            await self._process_batch(chunk, batch_id=i + 1)
            # Пауза, чтобы не словить 429
            await asyncio.sleep(1.0)

        log.info("ContentGen | task=finished")

    async def _process_batch(self, chunk: list[tuple[int, int]], batch_id: int):
        payload = []

        # 1. СБОР КОНТЕКСТА
        for x, y in chunk:
            node = await self.repo.get_node(x, y)
            if not node:
                continue

            # Безопасное получение тегов
            my_tags = []
            if node.flags and isinstance(node.flags, dict):
                my_tags = node.flags.get("biome_tags", [])

            surroundings = await self._get_surroundings_context(x, y)

            item = {
                "id": f"{x}_{y}",
                "internal_tags": my_tags,
                "surroundings": surroundings,
                "fill_content": {
                    "title": "",
                    "description": "",
                },
            }
            payload.append(item)

        if not payload:
            return

        # 2. ЗАПРОС К GEMINI
        response_text = ""
        try:
            log.debug(f"ContentGen | batch={batch_id} action=sending_request items={len(payload)}")

            response_text = await gemini_answer(
                mode="batch_location_desc",
                user_text=json.dumps(payload, ensure_ascii=False),
                max_tokens=4000,  # Оптимально для 5 элементов
            )

            # Чистка JSON
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            if not clean_json:
                raise ValueError("Empty response from LLM")

            result_map = json.loads(clean_json)

        except json.JSONDecodeError:
            log.error(
                f"ContentGen | batch={batch_id} status=llm_error err='JSON Decode Failed' raw_preview='{response_text[:100]}'"
            )
            return
        except (ValueError, TypeError) as e:
            # 🔥 FIX: Полный трейсбек ошибки, чтобы понять, что за 'error'
            log.error(f"ContentGen | batch={batch_id} status=llm_error exception='{e}'")
            log.error(traceback.format_exc())
            return

        # 3. СОХРАНЕНИЕ
        saved_count = 0
        for loc_id, content in result_map.items():
            try:
                x, y = map(int, loc_id.split("_"))

                original_item = next((i for i in payload if i["id"] == loc_id), None)
                tags = original_item["internal_tags"] if original_item else []

                final_content = {
                    "title": content.get("title", "Пустошь"),
                    "description": content.get("description", "..."),
                    "environment_tags": tags,
                }

                node_db = await self.repo.get_node(x, y)
                sec_id = node_db.sector_id if node_db else "D4"

                await self.repo.create_or_update_node(
                    x=x,
                    y=y,
                    sector_id=sec_id,
                    content=final_content,
                    is_active=True,
                )
                saved_count += 1

            except (ValueError, TypeError, KeyError) as e:
                log.error(f"ContentGen | save_error id={loc_id} err={e}")

        log.info(f"ContentGen | batch={batch_id} status=saved count={saved_count}/{len(chunk)}")

    async def _get_surroundings_context(self, x: int, y: int) -> dict[str, list[str]]:
        directions = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
        result = {}

        for dir_name, (dx, dy) in directions.items():
            nx, ny = x + dx, y + dy
            node = await self.repo.get_node(nx, ny)

            if node:
                tags = []
                if node.flags and isinstance(node.flags, dict):
                    tags = node.flags.get("biome_tags", [])
                    if node.flags.get("is_safe_zone"):
                        tags.append("safe_zone")

                if tags:
                    result[dir_name] = tags
            else:
                result[dir_name] = ["void"]

        return result
