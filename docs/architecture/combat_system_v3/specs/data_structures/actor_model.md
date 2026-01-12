# 🏗️ Actor Data Model (v3.1)

⬅️ [Назад](../README.md) | 🏠 [Документация](../../../../../README.md)

**Status:** Final
**Implementation:** `combat_internal_dto.py`, `schemas/combat.py`

Этот документ описывает структуру данных Актера (Игрока или Монстра) в боевой системе.
Модель оптимизирована для работы с **RedisJSON** и **Waterfall Calculator**.

---

## 1. Redis JSON Structure
Ключ: `combat:rbc:{sid}:actor:{id}`

Единый JSON-объект, содержащий все данные актера.

```json
{
  "meta": {
    "id": "101",
    "name": "Hero",
    "type": "player",
    "team": "blue",
    "is_ai": false,
    "template_id": "player:101",
    
    // Hot Data (State)
    "hp": 100,
    "max_hp": 150,
    "en": 50,
    "max_en": 100,
    "tactics": 0,
    "is_dead": false,
    "afk_level": 0,
    "tokens": {"gift": 1}
  },

  "raw": {
    // Cold Data (Source for Calculator)
    "attributes": {
      "strength": { "base": 10.0, "source": {"item:1": "+2"}, "temp": {} }
    },
    "modifiers": {
      "main_hand_damage_base": { "base": 0.0, "source": {"item:2": "+10"}, "temp": {} },
      "dodge_cap": { "base": 0.0, "source": {"item:3": "-0.25"}, "temp": {} }
      // ... все остальные модификаторы
    }
  },

  "skills": {
    // Skill Levels (Source for Resolver)
    "skill_swords": 0.55,
    "skill_heavy_armor": 0.30
  },

  "loadout": {
    // Equipment & Config (Mapping Slot -> Skill)
    "layout": {
      "main_hand": "skill_swords",
      "off_hand": "skill_shield_mastery",
      "chest_armor": "skill_medium_armor"
    },
    "belt": [
      { "item_id": "pot_1", "quantity": 5, "quick_slot_position": "quick_slot_1" }
    ],
    "known_abilities": ["fireball_1"],
    "tags": ["player", "heavy_armor_wearer"]
  },

  "active_abilities": [
    // Dynamic Effects
    { "uid": "uuid", "ability_id": "poison", "expire_at_exchange": 10 }
  ],

  "xp_buffer": {
    // XP Accumulator
    "dodge_success": 5
  },

  "metrics": {
    // Analytics Counters
    "damage_dealt": 500.0,
    "damage_taken": 100.0
  },

  "explanation": {
    // Debug Formulas (Optional, can be empty in Redis)
    "strength": "10 + 2"
  }
}
```

---

## 2. Python DTOs (Runtime)

### 2.1. ActorSnapshot
Зеркальное отражение Redis JSON. Используется в `CombatWorker`.

```python
class ActorSnapshot(BaseModel):
    meta: ActorMetaDTO
    raw: ActorRawDTO
    skills: dict[str, float]
    loadout: ActorLoadoutDTO
    active_abilities: list[ActiveAbilityDTO]
    xp_buffer: dict[str, int]
    metrics: dict[str, float]
    explanation: dict[str, str]
    
    # Calculated (In-Memory Cache)
    stats: ActorStats | None = None
    dirty_stats: set[str] = set()
```

### 2.2. ActorStats
Результат вычислений (`StatsEngine`). Используется в `CombatResolver`.
**Не сохраняется в Redis.**

```python
class ActorStats(BaseModel):
    # 1. Модификаторы (Результат WaterfallCalculator)
    mods: CombatModifiersDTO 
    
    # 2. Скиллы (Копия из Snapshot)
    skills: CombatSkillsDTO
```

---

## 3. Data Flow

### 3.1. Initialization (Context Assembler)
1.  Читает БД (Character, Items, Skills).
2.  Собирает `math_model` (raw + skills).
3.  Собирает `loadout` (layout + belt + tags).
4.  Собирает `meta` (hp, en).
5.  Инициализирует пустые `active_abilities`, `xp_buffer`, `metrics`.
6.  Отдает JSON для `CombatLifecycleService`.

### 3.2. Runtime Calculation (Stats Engine)
1.  Берет `ActorSnapshot`.
2.  Извлекает `raw` -> `WaterfallCalculator` -> `calculated_mods` + `explanation`.
3.  Извлекает `skills`.
4.  Создает `ActorStats(mods=calculated_mods, skills=skills)`.
5.  Сохраняет `stats` и `explanation` в Snapshot.

### 3.3. Combat Resolution (Resolver)
1.  Берет `ActorStats` (Attacker & Defender).
2.  Читает `stats.mods.damage_base`.
3.  Читает `stats.skills.skill_swords`.
4.  Считает результат.

### 3.4. Updates (Ability Service)
1.  Накладывает бафф -> Пишет в `snapshot.raw.modifiers...temp`.
2.  Ставит флаг `dirty_stats`.
3.  `StatsEngine` видит флаг -> Пересчитывает `ActorStats`.
