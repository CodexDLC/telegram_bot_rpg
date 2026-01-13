# Fencing Triggers (Фехтование)

⚠️ **Статус:** Design Concept (MVP)  
Не все предметы из этого списка добавлены в `game_data/items/`. Некоторые триггеры требуют балансировки и тестирования перед добавлением в игру.

---

## 🤺 Философия: Fencing (Фехтование)

**Ключевая идея:** «Ping 0ms». Искусство идеального тайминга, микроконтроля и поиска уязвимостей.

**Стиль игры:**
- Реактивная игра (парирование → контратака)
- Поиск уязвимостей (игнорирование защиты)
- Высокая точность, низкий базовый урон
- Дуэльный стиль (1v1)

**Слабости:**
- Низкий урон против тяжёлой брони (без триггеров)
- Требует высокой ловкости и восприятия
- Слабо против множественных противников

---

## 📊 Веса атрибутов

**Сумма весов:** 4

| Атрибут           | Вес | Роль                                    |
|-------------------|-----|-----------------------------------------|
| Agility (AGI)     | 2   | Скорость, парирование                   |
| Perception (PER)  | 1   | Точность уколов                         |
| Strength (STR)    | 1   | Урон (минимальный)                      |

---

## ⚔️ Типы оружия (Sub-types)

### Основные категории

| Тип             | Описание                              | Роль              |
|-----------------|---------------------------------------|-------------------|
| Daggers         | Кинжалы — скорость, скрытность        | Assassin          |
| Stilettos       | Стилеты — уколы, пробитие брони       | Anti-Armor        |
| Rapiers         | Рапиры — дистанция, контроль          | Duelist           |
| Smallswords     | Шпаги — молниеносные выпады           | Speed             |
| Main-gauches    | Даги — защита, Off-hand               | Parry/Counter     |
| Sai             | Сай — блокирование, захват оружия     | Control           |
| Estocs          | Эстоки — двуручные колющие (гибрид)   | Heavy Fencing     |
| Dirks           | Кортики — тяжёлые кинжалы             | Utility           |
| Rondels         | Рондели — пробитие лат                | Anti-Knight       |
| Katars          | Катары — тычковые ножи                | Burst             |

---

## 💎 Базовые типы оружия

### Stiletto (Стилет)

**Роль:** Anti-Armor

**Триггер:** `trigger_needle_point`

**Событие:** `ON_CRIT`

**Эффект:** Игнорирование **Flat Armor**

**Реализация:**
```python
"trigger_needle_point": {
    "event": "ON_CRIT",
    "chance": 1.0,
    "effect": "ignore_flat_armor",
    "metadata": {
        "armor_ignored_percent": 1.0
    }
}
```

---

### Smallsword (Шпага)

**Роль:** Speed / Initiative

**Триггер:** `trigger_tempo_gain`

**Событие:** `ON_CRIT`

**Эффект:** Бонусный токен `tempo`

**Реализация:**
```python
"trigger_tempo_gain": {
    "event": "ON_CRIT",
    "chance": 1.0,
    "effect": "grant_tempo_token",
    "metadata": {
        "tempo_tokens": 1
    }
}
```

---

### Kris (Крис)

**Роль:** DoT

**Триггер:** `trigger_laceration`

**Событие:** `ON_CRIT`

**Эффект:** Усиленное кровотечение (Heavy Bleed)

**Реализация:**
```python
"trigger_laceration": {
    "event": "ON_CRIT",
    "chance": 1.0,
    "effect": "apply_heavy_bleed",
    "metadata": {
        "damage_per_turn": 8,
        "duration": 4,
        "stack_limit": 3
    }
}
```

---

### Main-gauche (Дага / Off-hand)

**Роль:** Defensive / Counter-Attack

**Триггер:** `trigger_blade_catcher`

**Событие:** `ON_PARRY`

**Эффект:** Гарантированный токен `counter` → следующая атака +50% урона

**Реализация:**
```python
"trigger_blade_catcher": {
    "event": "ON_PARRY",
    "chance": 1.0,
    "effect": "grant_counter_token",
    "metadata": {
        "counter_tokens": 1,
        "damage_bonus": 0.5
    }
}
```

---

### Rapier (Рапира)

**Роль:** Precision

**Триггер:** `trigger_vitals_trace`

**Событие:** `ON_CRIT`

**Эффект:** Игнорирование **% Physical Resistance**

**Реализация:**
```python
"trigger_vitals_trace": {
    "event": "ON_CRIT",
    "chance": 1.0,
    "effect": "ignore_resistance",
    "metadata": {
        "resistance_ignored_percent": 1.0
    }
}
```

---

### Katar (Катар)

**Роль:** Assassin / Burst

**Триггер:** `trigger_vitals_strike`

**Событие:** `ON_CRIT`

**Эффект:** **True Damage** (игнорирует ВСЕ защиты)

**Реализация:**
```python
"trigger_vitals_strike": {
    "event": "ON_CRIT",
    "chance": 1.0,
    "effect": "deal_true_damage",
    "metadata": {
        "bypass_all_defenses": True
    }
}
```

---

### Sai (Сай / Off-hand)

**Роль:** Control / Debuff

**Триггер:** `trigger_disarm_chance`

**Событие:** `ON_PARRY`

**Эффект:** Временное снижение точности врага (-20%)

**Реализация:**
```python
"trigger_disarm_chance": {
    "event": "ON_PARRY",
    "chance": 0.5,
    "effect": "debuff_accuracy",
    "metadata": {
        "accuracy_reduction": -0.20,
        "duration": 2
    }
}
```

---

### Estoc (Эсток)

**Роль:** Heavy Fencing

**Триггер:** `trigger_heavy_piercing`

**Событие:** `ON_CRIT`

**Эффект:**
1. Игнорирование % резиста
2. Увеличенный множитель крита (x2.5)

**Реализация:**
```python
"trigger_heavy_piercing": {
    "event": "ON_CRIT",
    "chance": 1.0,
    "effect": "pierce_and_multiply",
    "metadata": {
        "resistance_ignored_percent": 1.0,
        "crit_multiplier": 2.5
    }
}
```

---

## 🎯 Базовые предметы (для game_data)

### Rapier (Рапира)
```python
BaseItemDTO(
    id="rapier",
    name_ru="Рапира",
    slot="main_hand",
    type="weapon",
    
    base_power=14,
    damage_spread=0.10,
    
    triggers=["trigger_vitals_trace"],
    
    allowed_materials=["ingots"],
    
    narrative_tags=["rapier", "duelist"]
)
```

### Katar (Катар)
```python
BaseItemDTO(
    id="katar",
    name_ru="Катар",
    slot="main_hand",
    type="weapon",
    
    base_power=10,
    damage_spread=0.15,
    
    triggers=["trigger_vitals_strike"],
    
    allowed_materials=["ingots"],
    
    narrative_tags=["katar", "assassin"]
)
```

### Main-gauche (Дага)
```python
BaseItemDTO(
    id="main_gauche",
    name_ru="Дага",
    slot="off_hand",
    type="weapon",
    
    base_power=6,
    damage_spread=0.15,
    
    triggers=["trigger_blade_catcher"],
    
    allowed_materials=["ingots"],
    
    narrative_tags=["dagger", "parrying"]
)
```

### Stiletto (Стилет)
```python
BaseItemDTO(
    id="stiletto",
    name_ru="Стилет",
    slot="main_hand",
    type="weapon",
    
    base_power=8,
    damage_spread=0.10,
    
    triggers=["trigger_needle_point"],
    
    allowed_materials=["ingots"],
    
    narrative_tags=["dagger", "piercing"]
)
```

---

## 🔧 Требования к реализации

### Минимальный MVP
1. ✅ `trigger_needle_point` — игнор flat armor
2. ✅ `trigger_vitals_trace` — игнор % resist
3. ✅ `trigger_blade_catcher` — контратака после парирования

### Расширенная версия
4. ⏳ `trigger_tempo_gain` — токены инициативы
5. ⏳ `trigger_vitals_strike` — true damage
6. ⏳ `trigger_laceration` — heavy bleed
7. ⏳ `trigger_disarm_chance` — обезоруживание

---

## 📚 Связанная документация

- **Система триггеров:** [README.md](./README.md)
- **DTO предметов:** [../01_item_dto_reference.md](../01_item_dto_reference.md)
- **Боевая система:** `/docs/architecture/combat_system_v3/`

---

**Последнее обновление:** Январь 2026  
**Статус:** Design Draft — требуется балансировка и тестирование