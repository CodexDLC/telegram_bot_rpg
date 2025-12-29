# Redis Actor Data Schema (v2.0)

Этот документ описывает детальную структуру JSON-объектов, хранящихся в полях `v:raw` и `v:cache` ключа актора (`combat:rbc:{sid}:actor:{char_id}`).

---

## 1. v:raw (Матрица Источников / Source of Truth)
**Назначение:** Хранит все исходные данные, влияющие на характеристики. Используется **только** для пересчета кеша. Если нужно изменить стат (например, наложить бафф), мы модифицируем этот JSON и инкрементируем `v:req_ver`.

### Концепция: Action-Based Values
Вместо простых чисел мы можем хранить **строковые инструкции** (как в `ScenarioEvaluator`). Это позволяет движку понимать намерение источника.

**Поддерживаемые операторы:**
*   `"+10"` — Добавить (Add).
*   `"-5"` — Отнять (Subtract).
*   `"*1.1"` — Умножить (Multiply). *Критично для процентов!*
*   `"=50"` — Установить (Set/Override). *Для жестких эффектов.*
*   `"1d6"` — Бросок кубика (опционально, если поддерживается).

### Структура JSON
```json
{
  "meta": {
    "type": "player",          // "player" | "monster" | "dummy"
    "archetype": "warrior",    // Опционально: класс/архетип
    "level": 10                // Уровень (влияет на формулы)
  },

  // === АТРИБУТЫ (Primary Stats) ===
  // Базовые характеристики из CharacterStatsReadDTO.
  // Структура значения: { "base": float, "flats": {source: val}, "percents": {source: val} }
  "attributes": {
    "strength": {
      "base": 15.0,
      "flats": {
        "buff:rage": "+10.0",       // Строка с операцией
        "debuff:weakness": "-5.0"
      },
      "percents": {
        "trait:giant": "+0.10"      // +10% (Аддитивно к базе)
      }
    },
    "agility": { "base": 10.0, "flats": {}, "percents": {} },
    "endurance": { "base": 12.0, "flats": {}, "percents": {} },
    "intelligence": { "base": 5.0, "flats": {}, "percents": {} },
    "wisdom": { "base": 5.0, "flats": {}, "percents": {} },
    "men": { "base": 5.0, "flats": {}, "percents": {} },
    "perception": { "base": 5.0, "flats": {}, "percents": {} },
    "charisma": { "base": 5.0, "flats": {}, "percents": {} },
    "luck": { "base": 5.0, "flats": {}, "percents": {} }
  },

  // === МОДИФИКАТОРЫ (Secondary Stats) ===
  // Характеристики из CharacterModifiersSaveDto.
  // Ключи должны совпадать с именами полей в DTO.
  // Структура значения: { "sources": {source_key: val} }
  "modifiers": {
    // Пример: Атака
    "physical_damage_min": {
      "sources": {
        "item:rusty_sword": "+25.0",
        "enchant:fire": "+5.0",
        "curse:weakness": "*0.5"    // Урезает урон в 2 раза (Мультипликативно)
      }
    },
    "physical_damage_max": {
      "sources": { "item:rusty_sword": "+35.0" }
    },
    
    // Пример: Защита
    "damage_reduction_flat": {
      "sources": { "item:chest_plate": "+15.0" }
    },
    "physical_resistance": {
      "sources": { "buff:stone_skin": "+0.15" } // +15%
    },

    // Пример: Скорость (Override)
    "move_speed": {
      "sources": {
        "base": "+1.0",
        "status:root": "=0.0"       // Жестко ставит 0
      }
    },

    // Пример: Вампиризм
    "vampiric_power": {
      "sources": { "item:blood_ring": "+0.05" }
    }
  },

  // === ТЕГИ (Tags) ===
  "tags": ["human", "melee", "heavy_armor"]
}
```

---

## 2. v:cache (Боевой Слепок / Calculated View)
**Назначение:** Готовый к употреблению объект с финальными значениями. Читается калькулятором урона (`CombatInteractionOrchestrator`) в каждом раунде.
**Важно:** Полностью соответствует структуре `CharacterModifiersSaveDto`.

### Структура JSON
```json
{
  "valid_for_ver": 12,  // Версия, для которой был рассчитан кеш

  "stats": {
    // Полный слепок CharacterModifiersSaveDto
    // Все значения - финальные числа (float/int)
    
    // 1. ❤️ РЕСУРСЫ
    "hp_max": 200,
    "hp_regen": 1.5,
    "energy_max": 100,
    "energy_regen": 0.5,
    "resource_cost_reduction": 0.0,

    // 2. ⚔️ ФИЗИЧЕСКАЯ АТАКА
    "physical_damage_min": 75.0,
    "physical_damage_max": 85.0,
    "physical_damage_bonus": 0.0,
    "physical_penetration": 0.0,
    "physical_accuracy": 1.0,
    "physical_crit_chance": 0.05,
    "physical_crit_power_float": 1.5,
    "physical_pierce_chance": 0.0,
    "physical_pierce_cap": 0.30,
    "physical_crit_cap": 0.75,

    // 3. 🔮 МАГИЧЕСКАЯ АТАКА
    "magical_damage_power": 0.0,
    "magical_damage_bonus": 0.0,
    "magical_penetration": 0.0,
    "magical_accuracy": 0.0,
    "magical_crit_chance": 0.01,
    "magical_crit_power_float": 1.5,
    "magical_crit_cap": 0.75,

    // 4. 🛡️ ЗАЩИТА
    "physical_resistance": 0.0,
    "magical_resistance": 0.0,
    "damage_reduction_flat": 15.0,
    "resistance_cap": 0.85,
    "dodge_chance": 0.05,
    "dodge_cap": 0.75,
    "debuff_avoidance": 0.0,
    "parry_chance": 0.0,
    "parry_cap": 0.50,
    "shield_block_chance": 0.0,
    "shield_block_power": 0.0,
    "shield_block_cap": 0.75,
    "anti_crit_chance": 0.0,
    "control_resistance": 0.0,

    // 5. 🔥 СТИХИИ
    "fire_damage_bonus": 0.0,
    "fire_resistance": 0.50,
    "water_resistance": 0.0,
    // ... air, earth, light, dark, poison, bleed ...
    "thorns_damage_flat": 0.0,

    // 6. ✨ СПЕЦИАЛЬНЫЕ
    "counter_attack_chance": 0.0,
    "vampiric_power": 0.05,
    "vampiric_trigger_chance": 1.0,
    "healing_power": 0.0,
    "pet_damage_bonus": 0.0,

    // 7. 🏞️ СРЕДА
    "environment_cold_resistance": 0.0,
    // ...

    // 8. 💰 ПРОЧЕЕ
    "move_speed": 1.0,     // (Если есть в DTO или добавляется динамически)
    "initiative": 10.0
  }
}
```

## 3. Логика Пересчета (Calculation Logic)

Процесс превращения `v:raw` в `v:cache`:

1.  **Парсинг Значений:**
    *   Все строковые значения (`"+10"`, `"*1.1"`) парсятся и применяются к базовому значению.
    *   Приоритет операций: `=` (Override) -> `*` (Multiply) -> `+`/`-` (Add/Sub).
2.  **Агрегация Атрибутов:**
    *   `Total = (Base + Sum(Flats)) * (1 + Sum(Percents))`
3.  **Расчет Производных (Derived Stats):**
    *   Используются формулы из `ModifiersCalculatorService`.
4.  **Агрегация Модификаторов:**
    *   `Total_Mod = ApplyAllSources(Base=0, Sources)`.
5.  **Финализация:**
    *   `Final_Stat = Derived_Stat + Total_Mod`.
6.  **Запись:**
    *   Формируется JSON `v:cache`.
    *   `valid_for_ver` устанавливается равным текущему `v:req_ver`.
    *   Записывается в Redis.
