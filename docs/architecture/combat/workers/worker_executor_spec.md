# Worker Executor Specification (The Muscle)

**Роль:** Выполнение приказа.
**Принцип:** "Eat what you take" (Никаких возвратов).

## Job: `execute_tick(ctx, sid, queue_key, lock_key, batch_size)`

### Логика:

1.  **Refresh Lock:**
    * `EXPIRE lock_key 60` (Продлеваем жизнь сессии).

2.  **Fetch Batch (1 RTT):**
    * `tasks_raw = Redis.LPOP(queue_key, count=batch_size)`
    * **IF Empty:** `DEL lock_key`, Return.

3.  **Load FULL Context (1 RTT):**
    * Загружаем `Meta` (для step_counter).
    * Загружаем **ВСЕХ** актеров (`:state`, `:cache`, `:effects`) через Pipeline.
    * *Примечание:* Для 1000 актеров это может занять 20-50мс, но это необходимо для консистентности.

4.  **Processing Loop (In-Memory):**
    * Инициализируем локальный контекст.
    * **FOR** `task` **IN** `tasks_raw`:
        * `Orchestrator.process(task, context)`
        * Все изменения пишутся в память.
        * Формируются логи и команды на удаление `moves`.

5.  **Commit (1 RTT):**
    * Отправляем `RedisPipeline`:
        * Обновления актеров (HSET, JSON.SET).
        * Новые логи (RPUSH).
        * Удаление обработанных заявок (JSON.DEL).
        * Обновление `meta:step_counter`.
    * `await pipeline.execute()`

6.  **Relay (Эстафета):**
    * Проверяем остаток: `Redis.LLEN(queue_key)`.
    * **IF > 0:**
        * `arq.enqueue_job("execute_tick", ..., batch_size)` (Зовем себя же).
    * **IF == 0:**
        * `DEL lock_key`.
