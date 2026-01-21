> ⚠️ **DRAFT / FEATURE REQUEST**
> Этот документ описывает концепцию системы завершения боя (Settlement).
> Требует доработки и адаптации под архитектуру v3.1.

# Техническая Документация: Модуль Завершения Боя (Combat Settlement & History)

## 1. Общая Концепция
Модуль отвечает за гарантированное сохранение результатов боя и асинхронную синхронизацию состояния боевой сессии (Redis) с постоянным хранилищем (PostgreSQL).

**Ключевая особенность:** Идемпотентность. Результат боя — это неизменяемый документ. Даже если игрок нажмет на кнопку через 3 часа, система должна найти этот документ и отобразить итог, вместо ошибки "Сессия не найдена".

---

## 2. Модель Данных: Combat Result Payload (Redis -> Worker)
Это JSON-структура, которую Combat Service (движок) формирует в момент окончания боя. Она содержит только разницу (Diff), которую нужно применить к базе данных.

**Важно про Инвентарь:** Так как в бою доступен только пояс, в отчете фигурируют только ID предметов, потраченных из пояса.

```json
{
  "session_id": "uuid-555-666",
  "meta": {
    "end_timestamp": 1735460000,
    "winner_team": "blue",
    "finish_reason": "victory" // victory | defeat | flee | draw
  },
  "participants": {
    "101": {  // ID Игрока
      "is_winner": true,
      
      // 1. Состояние для обновления "ac:{char_id}" (Status Cache)
      "state_snapshot": {
        "hp": 450,       // Игрок вышел побитым
        "energy": 20
      },

      // 2. ДИФФ для транзакции в БД (Settlement)
      "changes": {
        "xp_gained": 1250,
        "gold_gained": 100,
        
        // Только то, что реально потратили из пояса!
        // Worker должен найти эти предметы в inventory и сделать decrement
        "items_consumed": [
          { "inventory_id": 55, "item_template_id": "hp_pot_small", "qty": 2 }
        ],
        
        // Потеря прочности экипировки (если есть механика)
        "durability_loss": { "item:sword_epic": 5 }
      },

      // 3. Данные для UI (что показать игроку)
      "ui_report": {
        "damage_dealt": 5000,
        "loot_obtained": [
           {"name": "Шкура волка", "qty": 1} 
        ]
      }
    }
  },
  // Лог для реплея (опционально сжатый)
  "replay_log": [...] 
}
```

---

## 3. Схема БД: Таблица `combat_history`
Хранилище истины. Если сессии нет в Redis, правда лежит здесь.

```sql
CREATE TABLE combat_history (
    session_id UUID PRIMARY KEY,
    
    -- Для быстрого поиска "последнего боя" игрока
    -- Храним массив ID участников
    participant_ids BIGINT[] NOT NULL, 
    
    finished_at TIMESTAMP DEFAULT NOW(),
    
    -- Статус обработки транзакции начисления наград
    -- 'pending' (в очереди), 'processed' (начислено), 'failed' (ошибка)
    settlement_status VARCHAR(20) DEFAULT 'pending',
    
    -- Полный JSON отчета (см. п.2)
    result_payload JSONB NOT NULL
);

CREATE INDEX idx_combat_hist_participants ON combat_history USING GIN (participant_ids);
```

---

## 4. Workflows (Сценарии работы)

### Сценарий А: Штатное завершение (Фоновый процесс)
1.  **Combat Service (Engine):**
    *   Определяет конец боя (ХП монстра < 0).
    *   Формирует `CombatResultPayload`.
    *   Отправляет задачу в очередь: `task_queue.push("settle_combat", payload)`.
    *   **ВНИМАНИЕ:** Не удаляет сессию мгновенно, а выставляет ей TTL = 5 минут (на случай, если игрок прямо сейчас ждет ответа).
    *   Отвечает клиенту текущим снапшотом со статусом `finished`.

2.  **Settlement Worker (Фон):**
    *   Получает задачу.
    *   Создает запись в `combat_history` (Status: `pending`).
    *   **Транзакция БД:**
        *   `UPDATE characters SET xp = xp + delta ...`
        *   `UPDATE inventory SET amount = amount - qty WHERE id IN (...)` (Списываем расходники пояса).
        *   `INSERT INTO inventory ...` (Выдаем лут).
    *   Обновляет `combat_history` -> `processed`.
    *   Очищает Redis `cs:{session_id}` (если он еще жив).

### Сценарий Б: "Протухшая кнопка" (Telegram Case)
Игрок нажал "Атака" на сообщении 3-часовой давности.

**Логика Обработчика (Middleware / Turn Orchestrator):**

1.  **Попытка 1: Горячий кеш.**
    *   Ищем ключ `cs:{session_id}` в Redis.
    *   Результат: `None` (ключ умер по TTL).

2.  **Попытка 2: Проверка контекста игрока.**
    *   Ищем ключ `ac:{char_id}` (Account Cache).
    *   Проверяем поле `last_combat_session_id`.
    *   Сравниваем: `callback.session_id == ac.last_combat_session_id`.
    *   **Вывод:** "Игрок пытается взаимодействовать с боем, который был его последним состоянием, но боя в памяти уже нет". -> Значит, бой завершен.

3.  **Попытка 3: Cold Storage (Восстановление).**
    *   Идем в БД: `SELECT result_payload FROM combat_history WHERE session_id = :sid`.
    *   Если записи нет -> Ошибка "Бой устарел или не существует".
    *   Если запись есть -> Генерируем ответ.

4.  **Ответ пользователю:**
    *   Вместо обработки удара, мы отправляем сообщение:
        > "Бой уже завершен!"
        > Победитель: Синие
        > Награда: 100 золота
    *   (Опционально) Редактируем старое сообщение с кнопками, убирая кнопки "Атака", чтобы он не тыкал их снова.

---

## 5. Детали реализации Пояса (Belt Items)
Так как мы не грузим весь инвентарь в бой, синхронизация работает так:

1.  **Вход (Assembler):**
    *   Берем предметы из БД, которые помечены как `is_equipped=True` и лежат в слотах `belt_1`, `belt_2`.
    *   Копируем их `inventory_id` и `quantity` в `CombatSessionContainerDTO`.

2.  **Бой (Engine):**
    *   Игрок юзает банку.
    *   В Redis: `actor.belt_items[idx].quantity -= 1`.
    *   В лог потребления: `consumed.append({inv_id: 55, qty: 1})`.

3.  **Выход (Settler):**
    *   Worker берет список `items_consumed`.
    *   Выполняет SQL:
        ```sql
        UPDATE inventory 
        SET quantity = quantity - :qty 
        WHERE id = :inv_id AND character_id = :char_id;

        -- Удаление, если кончились
        DELETE FROM inventory WHERE quantity <= 0;
        ```

---

## 6. Что делать с кнопками (Telegram UX)
В Telegram кнопки живут вечно. Чтобы избежать спама запросами в БД:

1.  **Redis Cache "Finished":** Когда бой завершается, можно оставить в Redis "Могильный камень" (Tombstone) на 24 часа.
    *   Ключ: `combat:result_cache:{session_id}`
    *   Значение: Краткий JSON итога.
    *   Это быстрее, чем лезть в PostgreSQL `combat_history` каждый раз, когда игрок спамит кнопку.

2.  **Очистка интерфейса:** При отправке итогового сообщения, бот должен попытаться отредактировать предыдущее сообщение (само поле боя), заменив клавиатуру действий на кнопку "Посмотреть итог" или просто удалив клавиатуру.

---

## Резюме для разработки
1.  `Combat Service` должен стать чистым генератором данных. Он не пишет в базу, он возвращает `CombatResultPayload`.
2.  Нам нужен **Background Worker** (Celery / ARQ / Taskiq / asyncio.create_task), который разгребает очередь завершенных боев.
3.  Нам нужна таблица `combat_history`.
4.  В `CombatTurnOrchestrator` добавляем ветку `else`: если сессии нет в Redis, но ID совпадает с последним боем игрока — лезем в `combat_history` и отдаем результат.
