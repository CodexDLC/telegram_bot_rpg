# 💾 Inventory Session Schema (RedisJSON)

[⬅️ Назад: Inventory Data](./Resources.md)

---

## 🎯 Описание
Инвентарь хранится как **единый JSON документ** (RedisJSON).
Это позволяет выполнять частичное чтение и фильтрацию на стороне Redis (JSONPath).

**Redis Key:** `ac:{char_id}:inventory`
**Type:** `ReJSON` (Redis JSON)
**TTL:** 3600 sec (1 hour) - Sliding

---

## 🌳 JSON Structure

```json
{
  "char_id": 123,
  
  // Надетые предметы (Map: Slot -> Item)
  "equipped": {
    "head_armor": { ...ItemDTO... },
    "main_hand": { ...ItemDTO... }
  },

  // Предметы в сумке (Map: ItemID -> Item)
  "bag": {
    "1001": { 
      "inventory_id": 1001,
      "item_type": "weapon",
      "subtype": "sword",
      "data": { ... }
    }
  },

  // Кошелек и Ресурсы (Complex Structure)
  "wallet": {
    "currency": {
      "dust": 150,
      "tokens": 5
      // Gold отсутствует
    },
    "resources": {
      "wood": 50,
      "iron": 20
    },
    "components": {
      "gear": 2,
      "essence": 1
    }
  },

  // Метаданные и Статы
  "stats": {
    "max_weight": 100.0,
    "current_weight": 45.5,
    "slots_used": 10,
    "slots_total": 50
  },
  
  "is_dirty": false,
  "updated_at": 1715000000
}
```

---

## 🔍 JSONPath Queries (Примеры)

*   **Получить Валюту:** `$.wallet.currency`
*   **Получить Ресурсы:** `$.wallet.resources`
*   **Получить Пыль:** `$.wallet.currency.dust`
