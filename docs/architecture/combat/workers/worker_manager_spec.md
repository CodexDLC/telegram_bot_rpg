# Worker Manager Specification (The Brain)

**Роль:** Сбор задач, расчет нагрузки, запуск исполнителя.

## Job: `check_battle_state(session_id)`
**Триггер:** API (ход игрока).

### Логика:

1.  **Analyze Context:**
    * Получаем `meta.active_actors` (N).
    * Получаем длину очередей `moves`.

2.  **Calculate Batch Size (Adaptive):**
    * **IF** `N < 20` (Малый бой):
        * `batch_size = 100` (Забираем всё, контекст легкий).
    * **IF** `N >= 20` (Средний/Массовый):
        * `batch_size = 25` (Ограничиваем пачку, т.к. контекст тяжелый и расчеты долгие).

3.  **Harvest & Queue:**
    * Собираем задачи (Инстансы + Пары).
    * `RPUSH combat:rbc:{sid}:q:tasks ...`

4.  **Trigger Executor:**
    * Пытаемся взять лок: `SET ...:sys:busy 1 NX EX 60`
    * **IF Success:**
        * `arq.enqueue_job("execute_tick", session_id, "combat:rbc:{sid}:q:tasks", "combat:rbc:{sid}:sys:busy", batch_size)`
    * **IF Fail:**
        * Игнорируем (Воркер уже работает).

---

## Job: `afk_watchdog`
(Стандартная логика с проверкой move_id и наказанием).
