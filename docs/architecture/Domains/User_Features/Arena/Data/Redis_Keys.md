# 🔑 Arena Redis Keys

[⬅️ Назад: Arena Manifest](../Manifest.md)

## 🤖 AI CONTEXT
Описание ключей Redis, используемых `ArenaManager`.

## 📍 Prefix
Все ключи находятся в пространстве имен `arena:`.

## 📋 Keys Structure

### Queue (ZSET)
Очередь ожидания, сортированная по GearScore.
*   **Key:** `arena:queue:{mode}`
*   **Type:** `ZSET`
*   **Score:** `GearScore (float)`
*   **Member:** `char_id (int)`
*   **TTL:** Нет (удаляется при матче или отмене)

### Request Metadata (HASH)
Метаданные заявки игрока.
*   **Key:** `arena:request:{char_id}`
*   **Type:** `HASH`
*   **Fields:**
    *   `start_time`: timestamp (время начала поиска)
    *   `gs`: int (GearScore на момент заявки)
    *   `mode`: str (режим)
*   **TTL:** 300 секунд (5 минут) - авто-очистка мусора

## 📊 Пример данных

**arena:queue:1v1**
```
150.0 -> "1001"
165.0 -> "1002"
```

**arena:request:1001**
```
start_time: 1715000000.0
gs: 150
mode: "1v1"
```