# 💾 Data Structures

[⬅️ Назад: Context System](../README.md)

---

## 📋 Temp Context Hierarchy

### BaseTempContext
Общие поля для всех контекстов.
*   `meta`: {id, type, timestamp}

### CombatTempContext
*   `math_model`: {attributes, modifiers}
*   `loadout`: {equipment, abilities}
*   `vitals`: {hp, energy}

### InventoryTempContext
*   `items`: [InventoryItemDTO]
*   `wallet`: {gold, crystals}

### StatusTempContext
*   `stats_display`: {str: int}
*   `bio`: {name, level, class}
