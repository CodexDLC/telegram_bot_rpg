# 🎓 Refactoring: Tutorial System (Legacy to Core)

> **Status:** Planned
> **Target:** Pre-Alpha Release
> **Goal:** Заменить хардкодный Legacy-туториал на полноценный игровой сценарий, использующий реальные механики Game Core.

## 1. Проблема (Legacy State)
Текущий модуль `apps/bot/handlers/callback/tutorial` был написан на старте проекта.
*   **Fake Data:** Использует заглушки вместо реальной БД.
*   **No Core:** Не взаимодействует с `InventoryService`, `CombatManager`, `SkillService`.
*   **Hardcode:** Логика "зашита" в хэндлеры, что нарушает Clean Architecture.

## 2. Целевая Архитектура

### 2.1. TutorialService (Orchestrator)
Новый сервис в `apps/game_core/game_service/tutorial/tutorial_service.py`.
Он управляет потоком обучения, вызывая методы других сервисов.

**Обязанности:**
*   Управление состоянием FSM (шаги туториала).
*   Вызов `InventoryService` для выдачи стартового лута.
*   Вызов `SkillService` для разблокировки стартового навыка.
*   Инициализация тренировочного боя через `CombatManager`.

### 2.2. Схема Данных (Redis FSM)
Состояние игрока в туториале хранится в Redis.
*   **Key:** `fsm:{user_id}:{chat_id}:state` -> `TutorialState:StepX`
*   **Data:** `fsm:{user_id}:{chat_id}:data` ->
    ```json
    {
      "tutorial_progress": "combat_start",
      "chosen_item": "rusty_sword",
      "temp_combat_id": "uuid..."
    }
    ```

---

## 3. Сценарий (User Flow)

### Шаг 1: Пробуждение (The Awakening)
*   **Входная точка:** Игрок уже создал персонажа (имя, пол) и переведен в состояние `StartTutorial.start`.
*   **Лор:** Игрок приходит в себя в неизвестном месте (Рифт "Лимб"). "Ты видишь три предмета. Что поможет тебе выжить?"
*   **Действие:** Игроку предлагается выбрать **орудие**, а не класс.
    *   🗡️ Ржавый Меч
    *   🏹 Старый Лук
    *   🛡️ Потрескавшийся Щит
*   **Техника:** FSM переходит в `Tutorial:ItemSelection`.

### Шаг 2: Первый Лут и Навык (Real Core Services)
*   **Лор:** "Ты берешь оружие. Оно тяжелое, но надежное. В голове вспыхивает знание о том, как им пользоваться."
*   **Техника:** `TutorialService` на основе выбора:
    1.  Вызывает `InventoryService.add_item(char_id, item_id="rusty_sword")`.
    2.  Вызывает `InventoryService.equip_item(...)` (авто-экипировка).
    3.  Вызывает `SkillService.unlock_skill(char_id, skill_id="melee_combat")`.
    4.  Игрок видит сообщение: "Получено: Ржавый Меч [Common]. Изучен навык: Ближний бой."

### Шаг 3: Тренировочный Бой (Real Combat)
*   **Лор:** "Из тени выходит Искаженная Крыса. Бежать некуда."
*   **Техника:**
    1.  **Spawn:** `TutorialService` берет конфиг моба `tutorial_rat`.
    2.  **Init:** Вызов `CombatLifecycleService.create_battle(mode=CombatMode.TUTORIAL)`.
    3.  **Add:** Добавляет игрока и крысу в бой.
    4.  **Flow:** Игрок нажимает кнопки боя. `CombatManager` считает реальный урон.
    5.  **Hint:** Если игрок тупит, бот шлет подсказку: "Используй 'Удар', чтобы атаковать!".

### Шаг 4: Завершение и Хаб
*   **Лор:** Крыса повержена. Мир вокруг начинает таять. Ты просыпаешься в Городе (Хаб).
*   **Техника:**
    *   `CombatLifecycleService.finish_battle` определяет, что `mode=CombatMode.TUTORIAL`.
    *   `CombatXPManager` начисляет опыт (Level Up -> 2).
    *   `NavigationService` переносит игрока в `hub_center`.
    *   FSM сбрасывается в `GameState:World`.

---

## 4. Техническая Реализация (Tasks)

### 4.1. Конфиги (Game Data)
Создать файлы в `apps/game_core/resources/game_data/tutorial/`:

**`tutorial_mobs.py`**:
```python
TUTORIAL_RAT = {
    "id": "tutorial_rat",
    "name": "Искаженная Крыса",
    "stats": {"hp": 30, "damage": 2},
    "ai_behavior": "passive_aggressive" # Бьет слабо, иногда пропускает ход
}
```

**`tutorial_items.py`**:
```python
STARTER_GEAR = {
    "rusty_sword": {"item_id": "rusty_sword", "skill_id": "melee_combat"},
    "old_bow": {"item_id": "old_bow", "skill_id": "ranged_combat"},
    "cracked_shield": {"item_id": "cracked_shield", "skill_id": "shield"}
}
```

### 4.2. Методы в TutorialService
```python
class TutorialService:
    def __init__(self, session: AsyncSession, container: AppContainer, char_id: int):
        self.char_id = char_id
        self.inventory = InventoryService(session, char_id, ...)
        self.skill = SkillService(session, char_id, ...)
        self.combat_lifecycle = CombatLifecycleService(...)

    async def process_item_selection(self, item_key: str):
        # Выдача лута и скилла
        pass

    async def start_training_fight(self):
        # Вызов combat_lifecycle.create_battle(mode=CombatMode.TUTORIAL)
        pass
    
    async def complete_training_fight(self):
        # Логика после победы: выдача XP, перенос в хаб
        pass
```

### 4.3. Интеграция с Ботом
*   Переписать `apps/bot/handlers/callback/tutorial/*.py`.
*   Вместо простыни текста — вызовы `await tutorial_service.step_X()`.

### 4.4. Обработка Завершения Боя (Combat Outcome)
Необходимо модифицировать `CombatLifecycleService.finish_battle`. Эта логика должна быть консистентна с `Refactor_Combat_Finalization.md`.

1.  **При создании боя** в `TutorialService` мы передаем `mode=CombatMode.TUTORIAL`.
2.  **При завершении боя** `finish_battle` читает этот `mode` из метаданных сессии.
3.  **Логика ветвления:**
    ```python
    # В CombatLifecycleService.finish_battle
    # (предполагается, что CombatMode импортирован)
    async def finish_battle(self, session_id: str, winner_team: str):
        meta = await self.combat_manager.get_session_meta(session_id)
        combat_mode = meta.get("mode", CombatMode.ADVENTURE)

        match combat_mode:
            case CombatMode.ADVENTURE | CombatMode.RIFT:
                # Выдать лут, опыт и т.д.
                await self.loot_service.distribute_loot(...)
            case CombatMode.ARENA:
                # Обновить PvP рейтинг
                await self.arena_service.update_rating(...)
            case CombatMode.TUTORIAL:
                # Просто завершить бой и передать управление
                log.info("Tutorial combat finished.")
                # Вызывающий код (TutorialService) сам решит, что делать дальше
            case CombatMode.DUEL:
                log.info("Duel finished. No consequences.")
                pass
            case _:
                log.warning(f"Unknown combat mode: {combat_mode}")
    ```

---

## 5. Альтернативный Старт (Hardcore Option)
*В будущем можно рассмотреть вариант:*
1.  Игрок появляется в городе как "Безымянный".
2.  Говорит с NPC, берет квест.
3.  Его вырубают в подворотне -> Он очухивается в Рифте (Туториал).
*Это позволит бесшовно вписать обучение в открытый мир.*
