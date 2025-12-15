import os
import sys
from typing import cast

# --- Адаптация под структуру проекта ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from apps.game_core.resources.game_data.graf_data_world.world_config import BIOME_DEFINITIONS
    from apps.game_core.resources.game_data.monsters.spawn_config import BIOME_FAMILIES
except ImportError as e:
    print(f"❌ ОШИБКА ИМПОРТА: Не удалось загрузить конфигурацию мира. {e}")
    sys.exit(1)


def validate_world_config():
    print("🌍 ЗАПУСК ВАЛИДАЦИИ КОНФИГУРАЦИИ МИРА...\n")

    errors_found = False
    warnings_found = False

    # Обязательные поля для каждого тайла
    required_keys = {
        "spawn_weight": (int, float),
        "travel_cost": (int, float),
        "is_passable": (bool,),
        "visual_tags": (list,),
        "danger_mod": (int, float),
        "role": (str,),
        "narrative_hint": (str,),
    }

    valid_roles = {"background", "echo", "landmark"}

    # 1. ПРОВЕРКА BIOME_DEFINITIONS
    print("🔍 Проверка определений биомов (BIOME_DEFINITIONS)...")

    existing_biomes = set(BIOME_DEFINITIONS.keys())

    for biome_name, terrains in BIOME_DEFINITIONS.items():
        total_weight = 0.0

        if not terrains:
            print(f"🔴 [Structure Error] Биом '{biome_name}' пуст (нет типов местности).")
            errors_found = True
            continue

        for terrain_key, meta in terrains.items():
            # Проверка наличия ключей и типов
            for key, value in meta.items():
                if key in required_keys:
                    expected_types = required_keys[key]
                    if not isinstance(value, expected_types):
                        print(
                            f"🔴 [Type Error] {biome_name} -> {terrain_key}: Ключ '{key}' имеет неверный тип {type(value)}, ожидалось {expected_types}."
                        )
                        errors_found = True
                else:
                    print(f"🟠 [Key Warning] {biome_name} -> {terrain_key}: Обнаружен неопределенный ключ '{key}'.")
                    warnings_found = True

            for key in required_keys:
                if key not in meta:
                    print(f"🔴 [Key Error] {biome_name} -> {terrain_key}: Отсутствует обязательный ключ '{key}'.")
                    errors_found = True

            # Проверка логики значений
            if "role" in meta and meta["role"] not in valid_roles:
                print(
                    f"🔴 [Value Error] {biome_name} -> {terrain_key}: Недопустимая роль '{meta['role']}'. Разрешены: {valid_roles}"
                )
                errors_found = True

            if "spawn_weight" in meta:
                weight = cast(float, meta["spawn_weight"])
                if weight < 0:
                    print(f"🔴 [Logic Error] {biome_name} -> {terrain_key}: Отрицательный вес спавна.")
                    errors_found = True
                total_weight += weight

        # Проверка веса биома
        if total_weight == 0:
            print(
                f"🟠 [Logic Warning] Биом '{biome_name}': Сумма весов всех тайлов равна 0. Этот биом не сможет сгенерироваться процедурно."
            )
            warnings_found = True

    # 2. КРОСС-ВАЛИДАЦИЯ С МОНСТРАМИ
    print("\n🔍 Проверка связей с spawn_config.py...")

    for biome_in_spawn in BIOME_FAMILIES:
        if biome_in_spawn not in existing_biomes:
            print(
                f"🔴 [Cross-Link Error] В spawn_config.py указан биом '{biome_in_spawn}', которого нет в world_config.py!"
            )
            errors_found = True

    # --- ИТОГ ---
    print("\n---")
    if errors_found:
        print("❌ ВАЛИДАЦИЯ МИРА ЗАВЕРШЕНА С ОШИБКАМИ.")
    elif warnings_found:
        print("⚠️  ВАЛИДАЦИЯ МИРА ЗАВЕРШЕНА С ПРЕДУПРЕЖДЕНИЯМИ.")
    else:
        print("✅ КОНФИГУРАЦИЯ МИРА В ПОРЯДКЕ.")


if __name__ == "__main__":
    validate_world_config()
