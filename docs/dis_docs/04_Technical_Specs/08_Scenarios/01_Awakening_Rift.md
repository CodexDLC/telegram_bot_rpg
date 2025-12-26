# Сценарий: "Пробуждение в Рифте" (Awakening Rift)

**ID Квеста:** `awakening_rift`
**Тип:** Обучающий сценарий (Tutorial)
**Цель:** Познакомить игрока с базовыми механиками (выбор, статы, инвентарь) и создать начальный билд персонажа.

---

## 1. Общее описание
Игрок начинает игру в абстрактном пространстве "Рифт". Через серию текстовых событий и выборов он формирует свои начальные характеристики (Сила, Ловкость и т.д.) и получает стартовое снаряжение. В конце сценария персонаж переносится в основной игровой мир.

## 2. Механики

### 2.1. Накопление Статов (Weighted Stats)
Вместо прямого распределения очков, игрок делает сюжетные выборы, которые накапливают "веса" скрытых переменных:
*   `w_strength`, `w_agility`, `w_intelligence` и т.д.
*   `t_fire`, `t_water` (сродство со стихиями).

**Пример:**
> "Выбить дверь" -> `w_strength += 2`
> "Взломать замок" -> `w_agility += 2`

В конце сценария (`on_finalize`) система сортирует эти веса и распределяет стандартный массив характеристик (15, 14, 13...) в соответствии с приоритетами игрока.

### 2.2. Очередь Наград (Loot & Skills Queue)
Предметы и навыки не выдаются мгновенно. Они складываются во временные списки в контексте сессии:
*   `loot_queue`: `["push:sword_common", "push:potion_hp"]`
*   `skills_queue`: `["push:skill_power_strike"]`

При завершении квеста `TutorialHandler` материализует эти списки в реальные записи БД.

### 2.3. Logic Gates (Логические Врата)
Сценарий использует автоматические переходы для проверки условий.
*   **Пример:** Если `w_strength > w_agility`, игрок получает меч. Иначе — кинжал.
*   Это позволяет адаптировать награду под стиль игры, который игрок демонстрировал ранее.

## 3. Техническая Реализация

### Файлы
*   **JSON Контент:** `resources/game_data/scenarios/awakening_rift.json`
*   **Handler:** `apps/game_core/game_service/scenario_orchestrator/handlers/tutorial_handler.py`
*   **Orchestrator:** `ScenarioCoreOrchestrator` управляет потоком.

### Процесс (Pipeline)
1.  **Start:** `ScenarioCoreOrchestrator.initialize_scenario` вызывает `TutorialHandler.on_initialize`.
    *   Создается сессия в Redis.
    *   Инициализируются счетчики `w_*` и `t_*` нулями.
2.  **Step:** Игрок нажимает кнопки. `ScenarioDirector` обновляет счетчики в Redis.
3.  **Finalize:** При достижении терминальной ноды вызывается `TutorialHandler.on_finalize`.
    *   **Stats Calculation:** Сортировка `w_stats` -> Присвоение реальных статов в `ac:{char_id}`.
    *   **Loot Generation:** `InventoryRepo.create_item` для каждого ID из `loot_queue`.
    *   **Skill Unlock:** `SkillProgressRepo.unlock` для каждого ID из `skills_queue`.
    *   **Cleanup:** Удаление сессии и перевод игрока в мир.

## 4. Структура Данных (Context)

```json
{
  "quest_key": "awakening_rift",
  "current_node_key": "start_node",
  "w_strength": 5,
  "w_agility": 2,
  "loot_queue": ["sword_common"],
  "is_two_handed": 0
}
```
