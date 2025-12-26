# apps/game_core/game_service/scenario_orchestrator/handlers/tutorial_handler.py
import random
import uuid
from typing import Any

from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError

# Импортируем репозитории
from apps.common.database.repositories.ORM.inventory_repo import InventoryRepo
from apps.common.database.repositories.ORM.skill_repo import SkillProgressRepo
from apps.common.database.repositories.ORM.world_repo import WorldRepoORM
from apps.common.services.core_service import CombatManager
from apps.game_core.game_service.combat.combat_orchestrator_rbc import CombatOrchestratorRBC
from apps.game_core.game_service.monster.encounter_pool_service import EncounterPoolService

# Импортируем базы данных предметов для генерации
from apps.game_core.resources.game_data.items.bases import BASES_DB

from .base_handler import BaseScenarioHandler

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

        # Регистрируем состояние аккаунта
        await self.manager.update_account_state(char_id, context["quest_key"], session_id)

        # Сохраняем в Redis
        await self.manager.save_session_context(char_id, context)

        log.info(f"TutorialHandler | Start char={char_id} session={session_id}")
        return context

    async def on_finalize(self, char_id: int, context: dict[str, Any]) -> dict[str, Any]:
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

        # 5. ЗАПУСК БОЯ С МОНСТРОМ
        # Передаем целевую локацию, чтобы подобрать монстра под биом
        combat_session_id = await self._start_training_battle(char_id, target_exit_loc)

        await self.am.update_account_fields(
            char_id,
            {
                "state": "combat",  # Мы сейчас в бою
                "prev_state": "exploration",  # Возвращаемся в эксплорейшн
                "location_id": target_exit_loc,  # Мы уже "вышли" из рифта в случайную точку
                "prev_location_id": target_exit_loc,
            },
        )

        log.success(
            f"TutorialHandler | Finalization successful for char={char_id}. Battle started: {combat_session_id}. Exit loc: {target_exit_loc}"
        )

        # Возвращаем данные для оркестратора
        return {"combat_session_id": combat_session_id}

    async def _start_training_battle(self, char_id: int, target_loc: str) -> str:
        """Создает PVE бой с монстром, подходящим под локацию выхода."""

        # 1. Определяем параметры локации (Tier, Biome, Tags)
        world_repo = WorldRepoORM(self.db)
        try:
            x, y = map(int, target_loc.split("_"))
            node = await world_repo.get_node(x, y)

            # Дефолтные значения
            tier = 1
            biome = "wasteland"
            tags = ["ruins"]

            if node:
                # Пытаемся достать реальные данные
                content = node.content if isinstance(node.content, dict) else {}
                tags = content.get("environment_tags", tags)

                # Если есть зона, берем биом и тир оттуда
                if node.zone:
                    biome = node.zone.biome_id
                    tier = node.zone.tier
                else:
                    # Фоллбэк на флаги
                    tier = node.flags.get("threat_tier", tier)

        except (SQLAlchemyError, ValueError) as e:
            log.error(f"TutorialHandler | Failed to get world data for {target_loc}: {e}")
            tier, biome, tags = 1, "wasteland", ["ruins"]

        # 2. Ищем клан и монстра
        encounter_service = EncounterPoolService(self.db)
        clan = await encounter_service.get_random_encounter(tier, biome, tags)

        combat_manager = CombatManager(self.manager.redis)
        orchestrator = CombatOrchestratorRBC(self.db, combat_manager, self.am)

        config = {
            "battle_type": "pve_tutorial",
            "mode": "tutorial",
        }

        monster_orm = None
        if clan and clan.members:
            # Берем первого попавшегося монстра из клана (обычно миньон)
            # Можно добавить логику выбора по role='minion'
            monster_orm = clan.members[0]
            log.info(f"TutorialHandler | Selected tutorial monster: {monster_orm.name_ru} ({monster_orm.id})")
        else:
            # Фоллбэк, если база пустая (не должно случаться в проде)
            log.warning("TutorialHandler | No clan found for tutorial! Using dummy.")
            # В этом случае monster_orm останется None, и оркестратор создаст манекен (если мы не передадим его)
            # Но метод create_pve_battle_with_monster требует ORM объект.
            # Поэтому лучше здесь кинуть ошибку или создать фейковый объект, но пока оставим как есть
            # и используем старый метод start_battle если монстра нет
            pass

        if monster_orm:
            dashboard = await orchestrator.create_pve_battle_with_monster(
                player_id=char_id, monster=monster_orm, config=config
            )
        else:
            # Фоллбэк на старый метод с манекеном
            config["monster_variant"] = "dummy_tutorial"
            dashboard = await orchestrator.start_battle(players=[char_id], enemies=[], config=config)

        # Нам нужно установить статус игрока, чтобы он "видел" бой
        await combat_manager.set_player_status(char_id, f"combat:{dashboard.session_id}", ttl=3600)

        return dashboard.session_id

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

        # 1. Сохранение в Redis (для UI и кэша)
        await self.am.update_account_fields(char_id, {"stats": final_stats, "tokens": tokens})

    async def _process_loot(self, char_id: int, items: list[str]):
        """
        Выдача предметов через InventoryRepo.
        Берет данные из BASES_DB по ключу предмета.
        """
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
                log.warning(f"TutorialHandler | Item '{item_key}' not found in BASES_DB")
                continue

            # Определяем тип предмета для БД
            db_item_type = "resource"  # Default fallback

            if item_category in ["light_1h", "medium_1h", "melee_2h", "ranged", "shields"]:
                db_item_type = "weapon"
            elif item_category in ["heavy_armor", "medium_armor", "light_armor"]:
                db_item_type = "armor"
            elif item_category == "garment":
                db_item_type = "armor"  # Garment is light armor
            elif item_category == "accessories":
                db_item_type = "accessory"

            # Формируем данные предмета в зависимости от типа
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

            # Определяем слот для экипировки
            target_slot = item_data.get("slot")
            location = "inventory"
            equipped_slot = None

            # Если слот валидный, экипируем сразу
            if target_slot and target_slot != "misc":
                location = "equipped"
                equipped_slot = target_slot

            # Создаем через репозиторий
            try:
                await repo.create_item(
                    character_id=char_id,
                    item_type=db_item_type,
                    subtype=item_data.get("slot", "misc"),
                    rarity="common",
                    item_data=final_item_data,
                    location=location,
                    equipped_slot=equipped_slot,
                    quantity=1,
                )
            except Exception as e:  # noqa: BLE001
                log.error(f"TutorialHandler | Failed to create item {item_key}: {e}")

    async def _process_skills(self, char_id: int, skills: list[str]):
        """
        Выдача навыков через SkillProgressRepo.
        Разблокирует навыки (is_unlocked=True).
        """
        log.debug(f"TutorialHandler | Granting skills: {skills}")
        repo = SkillProgressRepo(self.db)

        # Разблокируем навыки
        await repo.update_skill_unlocked_state(char_id, skills, True)
