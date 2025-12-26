from typing import Any

from loguru import logger as log

from apps.common.database.model_orm.monster import GeneratedMonsterORM
from apps.common.schemas_dto import CharacterStatsReadDTO, CombatSessionContainerDTO, FighterStateDTO, StatSourceData
from apps.game_core.game_service.combat.core.combat_stats_calculator import StatsCalculator
from apps.game_core.game_service.status.modifiers_calculator_service import ModifiersCalculatorService
from apps.game_core.resources.game_data.items.bases import BASES_DB
from apps.game_core.resources.game_data.monsters.monster_equipment import MONSTER_EQUIPMENT_DB


class MonsterFactory:
    """
    Фабрика для создания боевых контейнеров монстров.
    Отвечает за превращение данных из БД в динамический объект боя.
    """

    @staticmethod
    def create_from_db(monster_orm: GeneratedMonsterORM, char_id: int, team: str = "red") -> CombatSessionContainerDTO:
        """
        Создает монстра на основе записи из базы данных (GeneratedMonsterORM).
        Единственная публичная точка входа.
        """
        # 1. Инициализация контейнера
        container = MonsterFactory._init_container(char_id, monster_orm, team)

        # 2. Базовые статы (из генерации)
        MonsterFactory._apply_base_stats(container, monster_orm.scaled_base_stats)

        # 3. Экипировка (Оружие, Броня, Когти и т.д.)
        # Добавляет статы в слой 'equipment'
        MonsterFactory._apply_equipment(container, monster_orm.loadout_ids)

        # 4. Скейлинг (Сила -> Урон, Выносливость -> Броня)
        # Сила всегда увеличивает урон, независимо от наличия оружия
        MonsterFactory._apply_scaling_logic(container)

        # 5. Вторичные характеристики (Крит, Уворот и т.д.)
        MonsterFactory._calculate_derived_modifiers(container)

        # 6. Финализация (ХП, Энергия, Скиллы)
        return MonsterFactory._finalize_state(container, monster_orm.skills_snapshot)

    @staticmethod
    def create_from_data(monster_data: dict[str, Any], char_id: int, team: str = "red") -> CombatSessionContainerDTO:
        """
        Создает монстра из словаря (для обратной совместимости с туториалом/тестами).
        """
        # Создаем фейковый ORM объект для переиспользования логики
        fake_orm = GeneratedMonsterORM(
            variant_key=monster_data.get("id", "unknown"),
            name_ru=monster_data.get("name_ru", monster_data.get("id", "Monster")),
            scaled_base_stats=monster_data.get("base_stats", {}),
            loadout_ids=monster_data.get("fixed_loadout", {}),
            skills_snapshot=monster_data.get("skills", []),
        )
        return MonsterFactory.create_from_db(fake_orm, char_id, team)

    # --- Внутренние методы сборки ---

    @staticmethod
    def _init_container(char_id: int, orm: GeneratedMonsterORM, team: str) -> CombatSessionContainerDTO:
        """Создает пустой контейнер с метаданными."""
        return CombatSessionContainerDTO(
            char_id=char_id,
            team=team,
            name=orm.name_ru,
            is_ai=True,  # Флаг для боевой системы
        )

    @staticmethod
    def _apply_base_stats(container: CombatSessionContainerDTO, stats: dict | Any):
        """Заполняет базовые статы из БД."""
        if not isinstance(stats, dict):
            return
        for stat, value in stats.items():
            if value:
                MonsterFactory._add_stat(container, stat, float(value), source="base")

    @staticmethod
    def _apply_equipment(container: CombatSessionContainerDTO, loadout: dict | Any):
        """
        Применяет статы предметов из loadout к контейнеру.
        Ищет в BASES_DB и MONSTER_EQUIPMENT_DB.
        """
        if not loadout:
            return

        # Если loadout это объект Pydantic, преобразуем в dict
        loadout_dict = loadout
        if hasattr(loadout, "model_dump"):
            loadout_dict = loadout.model_dump(exclude_none=True)

        if not isinstance(loadout_dict, dict):
            # Если вдруг пришел список или что-то другое, пропускаем пока
            # (В будущем можно добавить логику для списка)
            return

        for _slot, item_key in loadout_dict.items():
            if not item_key:
                continue

            # 1. Поиск предмета
            item_data = None
            item_category = None

            # Сначала в базе обычных предметов
            for category, items in BASES_DB.items():
                if item_key in items:
                    item_data = items[item_key]
                    item_category = category
                    break

            # Затем в базе монстров
            if not item_data:
                item_data = MONSTER_EQUIPMENT_DB.get(item_key)
                if item_data:
                    item_category = "monster_equipment"

            if not item_data:
                log.warning(f"MonsterFactory | Item '{item_key}' not found in DBs")
                continue

            # 2. Применение бонусов (Implicit Bonuses)
            bonuses = item_data.get("implicit_bonuses", {})
            for stat, val in bonuses.items():
                MonsterFactory._add_stat(container, stat, float(val), source="equipment")

            # 3. Специфичные статы (Урон оружия, Броня)
            base_power = float(item_data.get("base_power", 0))
            item_type = item_data.get("type")

            # Угадываем тип, если не указан
            if not item_type:
                if item_category in ["light_1h", "medium_1h", "melee_2h", "ranged", "shields"]:
                    item_type = "weapon"
                elif item_category in ["heavy_armor", "medium_armor", "light_armor", "garment", "accessories"]:
                    item_type = "armor"
                elif item_category == "shields":
                    item_type = "shield"

            if item_type == "weapon":
                spread = float(item_data.get("damage_spread", 0.1))
                dmg_min = base_power * (1.0 - spread)
                dmg_max = base_power * (1.0 + spread)

                MonsterFactory._add_stat(container, "physical_damage_min", dmg_min, source="equipment")
                MonsterFactory._add_stat(container, "physical_damage_max", dmg_max, source="equipment")

            elif item_type in ("armor", "garment", "accessory", "shield"):
                if base_power > 0:
                    MonsterFactory._add_stat(container, "damage_reduction_flat", base_power, source="equipment")

    @staticmethod
    def _apply_scaling_logic(container: CombatSessionContainerDTO):
        """
        Применяет правила мира:
        Сила -> Бонус к Физ. Урону.
        Выносливость -> Природная броня.
        """
        # Получаем полные статы (База + Экипировка)
        str_data = container.stats.get("strength")
        total_str = (str_data.base + str_data.equipment) if str_data else 0

        end_data = container.stats.get("endurance")
        total_end = (end_data.base + end_data.equipment) if end_data else 0

        # 1. Скейлинг Урона от Силы
        # Коэффициент 1.5 для монстров, чтобы они били больно даже без крутого оружия
        dmg_bonus = total_str * 1.5

        if dmg_bonus > 0:
            # Добавляем как базовый бонус (это свойство организма)
            MonsterFactory._add_stat(container, "physical_damage_min", dmg_bonus, source="base")
            MonsterFactory._add_stat(container, "physical_damage_max", dmg_bonus, source="base")
            log.debug(f"MonsterFactory | Str Scaling: +{dmg_bonus:.1f} dmg from {total_str} STR")

        # 2. Скейлинг Брони от Выносливости (Толстая шкура)
        natural_armor = total_end * 0.5
        if natural_armor > 0:
            MonsterFactory._add_stat(container, "damage_reduction_flat", natural_armor, source="base")

    @staticmethod
    def _calculate_derived_modifiers(container: CombatSessionContainerDTO):
        """Рассчитывает вторичные статы (Крит, Уворот) через сервис."""
        try:
            # Собираем DTO для калькулятора
            stats_dto = CharacterStatsReadDTO(
                character_id=0,  # Dummy
                strength=int(MonsterFactory._get_total(container, "strength")),
                agility=int(MonsterFactory._get_total(container, "agility")),
                endurance=int(MonsterFactory._get_total(container, "endurance")),
                intelligence=int(MonsterFactory._get_total(container, "intelligence")),
                wisdom=int(MonsterFactory._get_total(container, "wisdom")),
                men=int(MonsterFactory._get_total(container, "men")),
                perception=int(MonsterFactory._get_total(container, "perception")),
                charisma=int(MonsterFactory._get_total(container, "charisma")),
                luck=int(MonsterFactory._get_total(container, "luck")),
                created_at=None,
                updated_at=None,
            )
            derived_mods = ModifiersCalculatorService.calculate_all_modifiers_for_stats(stats_dto)

            # Добавляем рассчитанные модификаторы
            for mod_key, mod_value in derived_mods.model_dump().items():
                if isinstance(mod_value, (int, float)) and mod_value != 0:
                    # Вторички считаем как базовые свойства
                    MonsterFactory._add_stat(container, mod_key, float(mod_value), source="base")

        except Exception as e:  # noqa: BLE001
            log.error(f"MonsterFactory | Failed to calculate modifiers: {e}")

    @staticmethod
    def _finalize_state(container: CombatSessionContainerDTO, skills: list | Any) -> CombatSessionContainerDTO:
        """Финализирует состояние: ХП, Энергия, Скиллы."""
        # Расчет финальных значений
        final_stats = StatsCalculator.aggregate_all(container.stats)

        hp = int(final_stats.get("hp_max", 100))
        en = int(final_stats.get("energy_max", 40))

        container.state = FighterStateDTO(
            hp_current=hp, energy_current=en, targets=[], switch_charges=0, max_switch_charges=0, xp_buffer={}
        )

        # Скиллы
        # Приводим к списку строк ID
        clean_skills = []
        if skills:
            # Если skills это dict (из-за ORM), пробуем взять values или keys, или считаем что это ошибка
            # Но скорее всего это список, просто типизирован как dict
            iterable = skills
            if isinstance(skills, dict):
                # Если это словарь вида {id: level}, берем ключи
                iterable = skills.keys()

            for s in iterable:
                if isinstance(s, dict) and "id" in s:
                    clean_skills.append(str(s["id"]))
                else:
                    clean_skills.append(str(s))

        container.active_abilities = clean_skills

        log.debug(f"MonsterFactory | Created '{container.name}' (HP={hp}, EN={en})")
        return container

    # --- Утилиты ---

    @staticmethod
    def _add_stat(container: CombatSessionContainerDTO, key: str, value: float, source: str = "base"):
        if key not in container.stats:
            container.stats[key] = StatSourceData()

        if source == "base":
            container.stats[key].base += value
        elif source == "equipment":
            container.stats[key].equipment += value

    @staticmethod
    def _get_total(container: CombatSessionContainerDTO, key: str) -> float:
        if key not in container.stats:
            return 0.0
        data = container.stats[key]
        # В StatSourceData нет поля buffs, есть buffs_flat и buffs_percent
        # Для простоты считаем пока только базу и экипировку, так как баффов при создании еще нет
        return data.base + data.equipment
