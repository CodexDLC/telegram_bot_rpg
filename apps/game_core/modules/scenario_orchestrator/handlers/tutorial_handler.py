# apps/game_core/modules/scenario_orchestrator/handlers/tutorial_handler.py
import random
import uuid
from typing import TYPE_CHECKING, Any

from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError

# Импортируем репозитории
from apps.common.database.repositories.ORM.inventory_repo import InventoryRepo
from apps.common.database.repositories.ORM.skill_repo import SkillProgressRepo
from apps.common.database.repositories.ORM.world_repo import WorldRepoORM
from apps.common.schemas_dto.core_response_dto import CoreResponseDTO, GameStateHeader
from apps.common.schemas_dto.game_state_enum import GameState
from apps.common.schemas_dto.monster_dto import GeneratedMonsterDTO

# Импортируем базы данных предметов для генерации
from apps.game_core.resources.game_data.items.bases import BASES_DB
from apps.game_core.system.factories.monster.encounter_pool_service import EncounterPoolService

from .base_handler import BaseScenarioHandler

if TYPE_CHECKING:
    from apps.game_core.system.core_router import CoreRouter

# Список точек выхода из туториала (окрестности Хаба 52_52, радиус ~6 клеток)
TUTORIAL_EXIT_LOCATIONS = [
    "52_58",
    "52_46",
    "58_52",
    "46_52",  # Кардинальные направления
    "56_56",
    "48_56",
    "56_48",
    "48_48",  # Диагонали
    "55_57",
    "57_55",
    "49_57",
    "47_55",  # Случайные смещения
]


class TutorialScenarioHandler(BaseScenarioHandler):
    """
    Обработчик для квеста 'awakening_rift' (Туториал).
    Отвечает за подготовку контекста и выдачу финальных наград.
    """

    async def on_initialize(
        self, char_id: int, quest_master: dict[str, Any], prev_state: str | None = None, prev_loc: str | None = None
    ) -> dict[str, Any]:
        """Инициализация 'песочницы' туториала."""
        # Получаем session_id из quest_master (передан из оркестратора)
        session_id = quest_master.get("session_id")
        if not session_id:
            # Fallback если не передали (для совместимости)
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
            "p_loc": prev_loc,  # <-- Добавлено для совместимости с текстом сценария
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

        log.info(f"TutorialHandler | Start char={char_id} session={session_id}")
        return context

    async def on_finalize(self, char_id: int, context: dict[str, Any], router: "CoreRouter") -> CoreResponseDTO:
        """Финальная выдача наград и запуск боя."""
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

        # 4. ПОДМЕНА СОСТОЯНИЯ (FIX)
        # Выбираем случайную точку выхода вокруг Хаба
        target_exit_loc = random.choice(TUTORIAL_EXIT_LOCATIONS)

        # 5. ПОДГОТОВКА БОЯ (Выбор монстра через новый API)
        monster_dto = await self._find_tutorial_monster(target_exit_loc)

        # Обновляем аккаунт (ставим локацию выхода)
        # State ставим в combats, так как мы идем в бой
        await self.am.update_account_fields(
            char_id,
            {
                "state": GameState.COMBAT,
                "prev_state": GameState.EXPLORATION,
                "location_id": target_exit_loc,
                "prev_location_id": target_exit_loc,
            },
        )

        monster_name = monster_dto.name if monster_dto else "Unknown"
        log.success(
            f"TutorialHandler | Finalization successful for char={char_id}. Exit loc: {target_exit_loc}. Monster: {monster_name}"
        )

        # 6. ПЕРЕХОД В БОЙ (Через Router)
        # Передаем DTO монстра в контекст
        payload = await router.get_initial_view(
            target_state=GameState.COMBAT,
            char_id=char_id,
            session=self.db,
            action="initialize",
            context={
                "battle_type": "pve_tutorial",
                "monster_data": monster_dto.model_dump() if monster_dto else None,  # Передаем полный DTO
                "location_id": target_exit_loc,
            },
        )

        return CoreResponseDTO(header=GameStateHeader(current_state=GameState.COMBAT), payload=payload)

    async def _find_tutorial_monster(self, target_loc: str) -> GeneratedMonsterDTO | None:
        """
        Ищет подходящего монстра для туториала.
        Возвращает DTO монстра.
        """
        # 1. Определяем параметры локации (Tier, Biome, Tags)
        world_repo = WorldRepoORM(self.db)
        try:
            x, y = map(int, target_loc.split("_"))
            node = await world_repo.get_node(x, y)

            tier = 1
            biome = "wasteland"
            tags = ["ruins"]

            if node:
                content = node.content if isinstance(node.content, dict) else {}
                tags = content.get("environment_tags", tags)
                if node.zone:
                    biome = node.zone.biome_id
                    tier = node.zone.tier
                else:
                    tier = node.flags.get("threat_tier", tier)

        except (SQLAlchemyError, ValueError) as e:
            log.error(f"TutorialHandler | Failed to get world data for {target_loc}: {e}")
            tier, biome, tags = 1, "wasteland", ["ruins"]

        # 2. Ищем монстра через новый API
        encounter_service = EncounterPoolService(self.db)

        # Для туториала берем миньона (чтобы не убил сразу)
        monster_dto = await encounter_service.get_random_monster_dto(
            tier=tier,
            biome_id=biome,
            raw_tags=tags,
            role_filter="minion",  # Фильтруем только миньонов
        )

        if monster_dto:
            log.info(f"TutorialHandler | Selected tutorial monster: {monster_dto.name} ({monster_dto.id})")
            return monster_dto

        # Фоллбэк (если миньонов нет, берем любого)
        log.warning("TutorialHandler | No minion found, trying any role...")
        monster_dto = await encounter_service.get_random_monster_dto(tier=tier, biome_id=biome, raw_tags=tags)

        if monster_dto:
            return monster_dto

        log.warning("TutorialHandler | No monster found at all! Using dummy.")
        return None  # Пусть CombatOrchestrator создаст манекен

    # --- Приватные методы обработки наград ---

    async def _calculate_and_save_stats(self, char_id: int, context: dict[str, Any]):
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
        weighted_stats = []
        for name in stat_names:
            weight = context.get(f"w_{name}", 0)
            weighted_stats.append((name, weight))
        weighted_stats.sort(key=lambda x: x[1], reverse=True)
        bonuses = [9, 8, 7, 6, 5, 4, 3, 2, 1]
        final_stats = {}
        for i, (stat_name, _) in enumerate(weighted_stats):
            if i < len(bonuses):
                final_stats[stat_name] = bonuses[i]
        element_names = ["fire", "water", "earth", "air", "dark", "arcane", "light", "nature"]
        tokens = {f"t_{name}": context.get(f"t_{name}", 0) for name in element_names}
        await self.am.update_account_fields(char_id, {"stats": final_stats, "tokens": tokens})

    async def _process_loot(self, char_id: int, items: list[str]):
        log.debug(f"TutorialHandler | Granting items: {items}")
        repo = InventoryRepo(self.db)
        for item_key in items:
            item_data = None
            item_category = None
            for category, items_dict in BASES_DB.items():
                if item_key in items_dict:
                    item_data = items_dict[item_key]
                    item_category = category
                    break
            if not item_data:
                continue
            db_item_type = "resource"
            if item_category in ["light_1h", "medium_1h", "melee_2h", "ranged", "shields"]:
                db_item_type = "weapon"
            elif item_category in ["heavy_armor", "medium_armor", "light_armor", "garment"]:
                db_item_type = "armor"
            elif item_category == "accessories":
                db_item_type = "accessory"
            base_power = item_data.get("base_power", 0)
            final_item_data = {
                "name": item_data.get("name_ru", item_key),
                "description": item_data.get("description_ru", "Предмет из Рифта"),
                "base_price": 10,
                "components": {"base_id": item_key, "material_id": "tutorial_matter"},
                "durability": {
                    "current": item_data.get("base_durability", 100),
                    "max": item_data.get("base_durability", 100),
                },
                "bonuses": item_data.get("implicit_bonuses", {}),
                "valid_slots": [item_data.get("slot", "misc")],
            }
            if db_item_type == "weapon":
                final_item_data["damage_min"] = int(base_power * 0.8)
                final_item_data["damage_max"] = int(base_power * 1.2)
            elif db_item_type == "armor":
                final_item_data["protection"] = int(base_power)
            target_slot = item_data.get("slot")
            location = "inventory"
            equipped_slot = None
            if target_slot and target_slot != "misc":
                location = "equipped"
                equipped_slot = target_slot
            try:
                # Исправленный вызов с именованными аргументами
                await repo.create_item(
                    character_id=char_id,
                    item_type=db_item_type,
                    subtype=item_data.get("slot", "misc"),
                    rarity="common",
                    item_data=final_item_data,
                    location=location,
                    quantity=1,
                    equipped_slot=equipped_slot,
                )
            except Exception as e:  # noqa: BLE001
                log.error(f"TutorialHandler | Failed to create item {item_key}: {e}")

    async def _process_skills(self, char_id: int, skills: list[str]):
        log.debug(f"TutorialHandler | Granting skills: {skills}")
        repo = SkillProgressRepo(self.db)
        await repo.update_skill_unlocked_state(char_id, skills, True)
