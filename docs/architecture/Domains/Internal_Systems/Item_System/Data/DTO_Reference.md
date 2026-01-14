# Item DTO Reference (Справочник DTO)

[⬅️ Назад: Item System](../README.md) | [🏠 Архитектура (Root)](../../../../README.md)

---

## 📋 Обзор
Все предметы в игре представлены через полиморфные Pydantic DTO.

## 🏗️ Иерархия
*   **ItemCoreData** (Базовый класс)
    *   **WeaponData** (Оружие)
    *   **ArmorData** (Броня)
    *   **AccessoryData** (Аксессуары)
    *   **ConsumableData** (Расходники)
    *   **ResourceData** (Ресурсы)

---

## ⚔️ WeaponData (Оружие)
```python
class WeaponData(ItemCoreData):
    power: float              # Базовая сила
    spread: float = 0.1       # Разброс (±10%)
    accuracy: float = 0.0     # Базовая точность
    
    crit_chance: float = 0.0
    parry_chance: float = 0.0
    
    triggers: list[str]       # ["trigger_bleed"]
    
    grip: str                 # "1h", "2h"
    subtype: str              # "sword", "axe"
```

## 🛡️ ArmorData (Броня)
```python
class ArmorData(ItemCoreData):
    power: float              # Flat Damage Reduction
    
    evasion_penalty: float    # Штраф к увороту
    block_chance: float       # Только для щитов
    
    triggers: list[str] = []  # Всегда пусто
```

## 💍 AccessoryData (Аксессуары)
Используется только для бонусов (`bonuses`). Не имеет `power` или `durability`.

## 🧪 ConsumableData (Расходники)
*   `restore_hp`: int
*   `restore_energy`: int
*   `effects`: list[str] (Баффы)
*   `cooldown_rounds`: int

---

## 📦 Вспомогательные структуры

### ItemComponents
Хранит рецепт предмета:
*   `base_id`: "longsword"
*   `material_id`: "mat_iron"
*   `essence_id`: ["essence_fire"]

### ItemDurability
*   `current`: float
*   `max`: float
