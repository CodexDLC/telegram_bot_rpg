# apps/game_core/game_service/scenario_orchestrator/handlers/tutorial_handler.py
import uuid
from typing import Any

from loguru import logger as log

# Импортируем репозитории
from apps.common.database.repositories.ORM.inventory_repo import InventoryRepo
from apps.common.database.repositories.ORM.skill_repo import SkillProgressRepo

# Импортируем базы данных предметов для генерации
from apps.game_core.resources.game_data.items.bases import BASES_DB

from .base_handler import BaseScenarioHandler


class TutorialScenarioHandler(BaseScenarioHandler):
    """
    Обработчик для квеста 'awakening_rift' (Туториал).
    Отвечает за подготовку контекста и выдачу финальных наград.
    """

    async def on_initialize(
        self, char_id: int, quest_master: dict[str, Any], prev_state: str | None = None, prev_loc: str | None = None
    ) -> dict[str, Any]:
        """Инициализация 'песочницы' туториала."""
        session_id = str(uuid.uuid4())

        # Получаем данные симбиота для системных сообщений
        symbiote_data = await self.am.get_account_field(char_id, "symbiote")
        sys_name = "System"
        if isinstance(symbiote_data, dict):
            sys_name = symbiote_data.get("name", "System")
        elif isinstance(symbiote_data, str) and symbiote_data:
            sys_name = symbiote_data

        # Формируем стартовый контекст со всеми необходимыми ключами
        context = {
            "scenario_session_id": session_id,
            "quest_key": quest_master["quest_key"],
            "current_node_key": quest_master["start_node_id"],
            "step_counter": 0,
            "sys_actor": sys_name,
            "prev_state": prev_state,
            "prev_loc": prev_loc,
            # Веса статов (w_stats)
            "w_strength": 0,
            "w_agility": 0,
            "w_endurance": 0,
            "w_intelligence": 0,
            "w_wisdom": 0,
            "w_men": 0,
            "w_perception": 0,
            "w_charisma": 0,
            "w_luck": 0,
            # Веса стихий (t_elements)
            "t_fire": 0,
            "t_water": 0,
            "t_earth": 0,
            "t_air": 0,
            "t_dark": 0,
            "t_arcane": 0,
            "t_light": 0,
            "t_nature": 0,
            # Очереди наград
            "loot_queue": [],
            "skills_queue": [],
            # Флаги логики
            "is_two_handed": 0,
        }

        # Регистрируем состояние аккаунта
        await self.manager.update_account_state(char_id, context["quest_key"], session_id)

        # Сохраняем в Redis
        await self.manager.save_session_context(char_id, context)

        log.info(f"TutorialHandler | Start char={char_id} session={session_id}")
        return context

    async def on_finalize(self, char_id: int, context: dict[str, Any]):
        """Финальная выдача наград и обновление профиля."""
        log.info(f"TutorialHandler | Finalizing char={char_id}")

        # 1. Расчет статов (+9...+1)
        await self._calculate_and_save_stats(char_id, context)

        # 2. Материализация предметов (Loot)
        loot_list = context.get("loot_queue", [])
        if loot_list:
            await self._process_loot(char_id, loot_list)

        # 3. Активация навыков (Skills)
        skills_list = context.get("skills_queue", [])
        if skills_list:
            await self._process_skills(char_id, skills_list)

        log.success(f"TutorialHandler | Finalization successful for char={char_id}")

    # --- Приватные методы обработки наград ---

    async def _calculate_and_save_stats(self, char_id: int, context: dict[str, Any]):
        """Логика расчета статов и сохранения токенов."""
        stat_names = [
            "strength",
            "agility",
            "endurance",
            "intelligence",
            "wisdom",
            "men",
            "perception",
            "charisma",
            "luck",
        ]

        # Сбор и сортировка
        weighted_stats = []
        for name in stat_names:
            weight = context.get(f"w_{name}", 0)
            weighted_stats.append((name, weight))

        weighted_stats.sort(key=lambda x: x[1], reverse=True)

        # Распределение бонусов
        bonuses = [9, 8, 7, 6, 5, 4, 3, 2, 1]
        final_stats = {}
        for i, (stat_name, _) in enumerate(weighted_stats):
            if i < len(bonuses):
                final_stats[stat_name] = bonuses[i]

        # Сбор токенов
        element_names = ["fire", "water", "earth", "air", "dark", "arcane", "light", "nature"]
        tokens = {f"t_{name}": context.get(f"t_{name}", 0) for name in element_names}

        # Сохранение в аккаунт
        await self.am.update_account_fields(char_id, {"stats": final_stats, "tokens": tokens})

    async def _process_loot(self, char_id: int, items: list[str]):
        """
        Выдача предметов через InventoryRepo.
        Берет данные из BASES_DB по ключу предмета.
        """
        log.debug(f"TutorialHandler | Granting items: {items}")
        repo = InventoryRepo(self.db)

        for item_key in items:
            # Ищем предмет в глобальной базе
            # В BASES_DB ключи - это категории (weapons, armor...), внутри них - ключи предметов
            # Нам нужно найти категорию, в которой лежит item_key

            item_data = None
            item_category = None

            for category, items_dict in BASES_DB.items():
                if item_key in items_dict:
                    item_data = items_dict[item_key]
                    item_category = category
                    break

            if not item_data:
                log.warning(f"TutorialHandler | Item '{item_key}' not found in BASES_DB")
                continue

            # Создаем предмет
            # Для туториала выдаем предметы обычной редкости (common)
            # item_type берем из категории (weapon, armor...)
            # subtype берем из слота или типа урона (упрощенно)

            # Определяем тип предмета для БД
            db_item_type = "unknown"
            if item_category == "weapons":
                db_item_type = "weapon"
            elif item_category == "armor":
                db_item_type = "armor"
            elif item_category == "garment":
                db_item_type = "garment"
            elif item_category == "accessories":
                db_item_type = "accessory"

            # Создаем через репозиторий
            await repo.create_item(
                character_id=char_id,
                item_type=db_item_type,
                subtype=item_data.get("slot", "misc"),  # Используем слот как подтип
                rarity="common",
                item_data={
                    "base_id": item_key,
                    "name": item_data.get("name_ru", item_key),
                    "power": item_data.get("base_power", 0),
                    "durability": item_data.get("base_durability", 100),
                    "bonuses": item_data.get("implicit_bonuses", {}),
                },
                location="inventory",
                quantity=1,
            )

    async def _process_skills(self, char_id: int, skills: list[str]):
        """
        Выдача навыков через SkillProgressRepo.
        Разблокирует навыки (is_unlocked=True).
        """
        log.debug(f"TutorialHandler | Granting skills: {skills}")
        repo = SkillProgressRepo(self.db)

        # Разблокируем навыки
        await repo.update_skill_unlocked_state(char_id, skills, True)
