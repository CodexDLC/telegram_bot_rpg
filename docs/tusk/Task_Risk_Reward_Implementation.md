# 🛠️ Tech Task: Implementation of Risk & Reward System

> **Status:** Ready for Dev
> **Epics:** Economy, Exploration, Combat
> **Dependencies:** Inventory System, World Navigation

## 🟢 Phase 1: Database Layer (Foundation)

Закладываем фундамент данных.
*(Примечание: Так как Alembic еще не настроен, изменения требуют пересоздания таблиц `seed_world_gen.py` или ручного `ALTER TABLE`)*

### [DB-01] Schema Update: Inventory Flags
*   **Target:** `apps/common/database/model_orm/inventory.py` -> `InventoryItem`
*   **Задача:** Добавить поле для разделения "чистых" и "грязных" вещей.
*   **Изменения:**
    ```python
    is_secured: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)
    ```
*   **Индекс:** Добавить `Index` на `(character_id, is_secured)` для быстрой выборки лута при смерти.

### [DB-02] Schema Update: XP Checkpoints
*   **Target:** `apps/common/database/model_orm/character.py` -> `CharacterStats`
*   **Задача:** Добавить поле для хранения "сохраненного опыта".
*   **Изменения:**
    ```python
    secured_xp: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    ```

---

## 🔵 Phase 2: Game Core Services (Logic)

Учим "мозг" игры работать с новыми правилами.

### [CORE-01] Inventory Service Update
*   **Target:** `apps/game_core/game_service/inventory/inventory_service.py`
*   **Задача:** Научить метод `add_item` принимать контекст.
*   **Логика:**
    *   Обновить сигнатуру: `add_item(..., is_secured: bool = True)`.
    *   Если источник = Рифт/Моб из Рифта -> передаем `False`.
*   **Новый метод:** `secure_all_items(char_id)` — массовый `UPDATE inventory SET is_secured = true WHERE char_id = X`.

### [CORE-02] Navigation Triggers (Safe Zones)
*   **Target:** `apps/bot/ui_service/navigation_service.py` -> `move_player`
*   **Задача:** Связать перемещение игрока с сохранением.
*   **Логика:**
    1.  Получаем `target_loc_data`.
    2.  Если `flags['is_safe_zone'] == True`:
        *   Вызываем `inventory_service.secure_all_items()`.
        *   Вызываем `xp_manager.checkpoint_xp()`.
        *   Отправляем уведомление: "Данные синхронизированы".

### [CORE-03] XP Manager Logic
*   **Target:** `apps/game_core/game_service/combat/combat_xp_manager.py`
*   **Задача:** Разделить начисление опыта.
*   **Логика:**
    *   `add_xp()`: Обновляет только `total_xp` (текущий опыт).
    *   `checkpoint_xp()`: Копирует `total_xp` -> `secured_xp`.

---

## 🔴 Phase 3: Death Mechanics (The Grinder)

Самая сложная часть. Обработка смерти.

### [DEATH-01] Loot Filtering Strategy
*   **Target:** `apps/game_core/game_service/combat/combat_lifecycle_service.py` -> `_finalize_adventure`
*   **Задача:** Реализовать потерю лута при смерти в Рифте.
*   **Логика:**
    1.  Если `mode == RIFT` и игрок проиграл:
    2.  `lost_items = inventory_repo.get_unsecured_items(char_id)`
    3.  `inventory_repo.delete_items([i.id for i in lost_items])`
    4.  Передать `lost_items` в `CorpseManager`.

### [DEATH-02] XP Rollback
*   **Target:** `apps/game_core/game_service/combat/combat_xp_manager.py`
*   **Задача:** Реализовать штраф по опыту.
*   **Логика:**
    *   Метод `rollback_xp(char_id)`:
    *   `current_xp = max(secured_xp, current_xp - penalty)` (чтобы не уйти в минус ниже сейва).

---

## 🟣 Phase 4: Redis Corpse System (Persistence)

Временное хранилище потерянного.

### [REDIS-01] Corpse Data Structure
*   **Target:** `apps/common/schemas_dto/world_stats_dto.py` (или новый файл)
*   **Schema:**
    ```python
    class CorpseDTO(BaseModel):
        owner_id: int
        items: list[InventoryItemDTO]
        xp_lost: int
        expires_at: float
    ```

### [REDIS-02] Corpse Manager
*   **Target:** `apps/common/services/core_service/manager/world_manager.py` (расширение)
*   **Задача:** Управление жизненным циклом трупа.
*   **Методы:**
    *   `create_corpse(loc_id, data)`: `SETEX corpse:{loc_id}:{char_id} 3600 ...`
    *   `claim_corpse(loc_id, char_id)`: Возврат вещей в инвентарь (снова как `Unsecured`!).

---

## 🟡 Phase 5: UI & UX (Telegram)

Чтобы игрок понимал, что происходит.

### [UI-01] Inventory Visualization
*   **Target:** `apps/bot/ui_service/helpers_ui/formatters/inventory_formatter.py`
*   **Задача:** Добавить маркер для незащищенных вещей.
*   **Пример:** `⚠️ Ржавый меч` или `[UNSECURED] Ржавый меч`.

### [UI-02] Death Screen Info
*   **Target:** `apps/bot/resources/texts/game_messages/combat_messages.py`
*   **Задача:** Обновить сообщение о смерти.
*   **Текст:** "Связь потеряна. Вы потеряли: 5 предметов, 200 XP. Тело останется в Рифте еще 60 минут."
