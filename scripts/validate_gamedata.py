import os
import sys

# --- Адаптация под структуру проекта ---
# Добавляем корень проекта в sys.path, чтобы можно было импортировать из 'apps'
# Скрипт находится в /scripts, корень проекта - на уровень выше
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# --- MOCKS & IMPORTS SETUP ---

from backend.resources.game_data import (  # noqa: E402
    ALL_FAMILIES_RAW,
    SKILL_MAPPING,  # noqa: E402
    get_family_config,
)
from backend.resources.game_data.monsters.spawn_config import BIOME_FAMILIES, TIER_AVAILABILITY  # noqa: E402


def validate_monsters():
    """
    Скрипт для валидации игровой логики монстров.
    Проверяет целостность данных в файлах семейств, скиллов и конфигурации спавна.
    """
    print("🔍 ЗАПУСК ВАЛИДАЦИИ ИГРОВЫХ ДАННЫХ МОНСТРОВ...\n")

    errors_found = False
    warnings_found = False

    # 1. СБОР ВСЕХ СИСТЕМНЫХ СКИЛЛОВ
    valid_system_skills = set(SKILL_MAPPING.keys())
    valid_flavor_skills: set[str] = set()
    for variants_list in SKILL_MAPPING.values():
        valid_flavor_skills.update(variants_list)

    print(f"✅ Загружено {len(valid_system_skills)} архетипов скиллов и {len(valid_flavor_skills)} их вариаций.")

    # 2. ПРОВЕРКА СЕМЕЙСТВ
    print("\n🔍 Проверка файлов семейств...")
    all_family_ids_from_files = {f["id"] for f in ALL_FAMILIES_RAW}

    for family_raw in ALL_FAMILIES_RAW:
        fam_id = family_raw.get("id", "N/A")
        if fam_id == "N/A":
            print("🔴 [Critical Error] В одном из файлов семейств отсутствует ключ 'id'!")
            errors_found = True
            continue

        family_dto = get_family_config(fam_id)
        if not family_dto:
            print(f"🔴 [Critical Error] Не удалось загрузить DTO для семьи: {fam_id}")
            errors_found = True
            continue

        variants = family_dto.variants
        hierarchy = family_dto.hierarchy

        # --- Проверка А: Целостность иерархии ---
        all_hierarchy_ids: set[str] = set()
        for rank, unit_ids in hierarchy.model_dump().items():
            for uid in unit_ids:
                all_hierarchy_ids.add(uid)
                if uid not in variants:
                    print(f"🔴 [Hierarchy Error] {fam_id}: В иерархии '{rank}' указан '{uid}', но его нет в variants!")
                    errors_found = True

        # --- Проверка Б: Сироты (есть в variants, нет в иерархии) ---
        for vid in variants:
            if vid not in all_hierarchy_ids:
                print(
                    f"🟠 [Warning] {fam_id}: Юнит '{vid}' описан в variants, но не включен ни в одну группу hierarchy."
                )
                warnings_found = True

        # --- Проверка В: Скиллы, Тиры и Стоимость ---
        for vid, data in variants.items():
            # Скиллы
            skills = data.skills
            for sk in skills:
                if sk not in valid_system_skills and sk not in valid_flavor_skills:
                    print(f"🔴 [Skill Error] {fam_id} -> {vid}: Скилл '{sk}' не найден в skills_todo_list.")
                    errors_found = True

            # Ключи
            if data.min_tier is None:
                print(f"🔴 [Data Error] {fam_id} -> {vid}: Отсутствует ключ 'min_tier'.")
                errors_found = True
            if data.max_tier is None:
                print(f"🔴 [Data Error] {fam_id} -> {vid}: Отсутствует ключ 'max_tier'.")
                errors_found = True
            if data.cost is None:
                print(f"🔴 [Data Error] {fam_id} -> {vid}: Отсутствует ключ 'cost'.")
                errors_found = True

    # 3. ПРОВЕРКА КОНФИГУРАЦИИ СПАВНА
    print("\n🔍 Проверка конфигурации спавна (spawn_config.py)...")

    # --- Проверка А: BIOME_FAMILIES ---
    for biome, allowed_families in BIOME_FAMILIES.items():
        for fam_id in allowed_families:
            if fam_id not in all_family_ids_from_files:
                print(
                    f"🔴 [Spawn Error] Биом '{biome}': Разрешена семья '{fam_id}', но она не загружена из файлов (нет в ALL_FAMILIES_RAW)."
                )
                errors_found = True

    # --- Проверка Б: TIER_AVAILABILITY (Logic Gaps) ---
    for tier, allowed_families in TIER_AVAILABILITY.items():
        if "all_families" in allowed_families:
            continue

        for fam_id in allowed_families:
            family_obj = get_family_config(fam_id)
            if not family_obj:
                print(
                    f"🔴 [Spawn Error] Tier {tier}: Разрешена семья '{fam_id}', но она не загружена в ALL_FAMILIES_RAW."
                )
                errors_found = True
                continue

            # Эмулируем логику get_available_variants_for_tier
            valid_units: list[str] = []
            for uid, data in family_obj.variants.items():
                min_t = data.min_tier
                max_t = data.max_tier
                if min_t is not None and max_t is not None and min_t <= tier <= max_t:
                    valid_units.append(uid)

            if not valid_units:
                print(
                    f"🟠 [Logic Gap] Tier {tier}: Разрешена семья '{fam_id}', но у неё НЕТ юнитов для этого уровня (проверьте min/max_tier)."
                )
                warnings_found = True

    # --- ИТОГ ---
    print("\n---")
    if errors_found:
        print("❌ ВАЛИДАЦИЯ ЗАВЕРШЕНА С КРИТИЧЕСКИМИ ОШИБКАМИ. ИСПРАВЬТЕ ИХ ПЕРЕД ЗАПУСКОМ.")
    elif warnings_found:
        print("⚠️  ВАЛИДАЦИЯ ЗАВЕРШЕНА С ПРЕДУПРЕЖДЕНИЯМИ. Критических ошибок нет, но есть логические несостыковки.")
    else:
        print("✅ ВАЛИДАЦИЯ ПРОШЛА УСПЕШНО. Критических ошибок и предупреждений не найдено.")


if __name__ == "__main__":
    validate_monsters()
