# Feature: Feint System & Token Economy (Target-Centric UI)

⬅️ [Назад](../../README.md)

**Status:** Approved Architecture
**Components:** `FeintService`, `TokenService`, `ViewService`, `MechanicsService`, `TurnManager`.

Этот документ описывает финальную архитектуру системы финтов, где боевые кнопки (Рука) привязаны к контексту Цели.

---

## 1. Концепция UI: "Target-Centric"

Интерфейс игрока зависит от наличия активной цели.

### A. Status: Waiting (Нет цели)
*   **Условие:** Очередь целей (`targets:{id}`) пуста.
*   **UI:** Анимация ожидания ("⏳ Поиск противника...").
*   **Кнопки:** Боевые кнопки отсутствуют. Доступны только системные ("Обновить", "Сбежать").

### B. Status: Active (Есть цель)
*   **Условие:** В очереди есть цель.
*   **UI:** Карточка противника + Боевая клавиатура.
*   **Кнопки (внутри объекта Цели):**
    1.  **Базовые Атаки:** Всегда доступны (0 токенов).
    2.  **Финты (Feints):** Куплены за токены (Pre-Paid).
    3.  **Магия/Предметы:** Дополнительные действия.

---

## 2. Структура DTO (Data Transfer Objects)

### CombatActionBtn
Единая структура для любой кнопки действия.
```python
class CombatActionBtn(BaseModel):
    label: str       # "⚔️ Сокрушительный удар"
    action_id: str   # "hash_123" (ссылка на карту в руке)
    is_active: bool  # True
    type: str        # "attack", "magic", "item" (для группировки в UI)
```

### ActorFullInfo (Target Context)
```python
class ActorFullInfo(BaseModel):
    # Стандартные поля (HP, Name...)
    char_id: int
    # ...
    
    # КНОПКИ (Actions Payload)
    # Заполняется ТОЛЬКО если это Target.
    # Если это Hero, поле None.
    available_actions: Optional[List[CombatActionBtn]] = None 
```

### CombatDashboardDTO
```python
class CombatDashboardDTO(BaseModel):
    status: str      # "active" | "waiting" | "finished"
    
    hero: ActorFullInfo             # actions = None
    target: Optional[ActorFullInfo] # actions = [Btn1, Btn2...] (если status="active")
    
    system_actions: List[CombatActionBtn] # ["Обновить", "Сбежать"]
```

---

## 3. Алгоритм "Покупки" (The Buyer)

Выполняется в `ViewService` (через `FeintService`) при генерации Dashboard.

1.  **Check Target:** Проверяем очередь целей. Если пусто -> `status="waiting"`, выход.
2.  **Check Hand:** Проверяем текущую руку в Redis. Если полная -> пропускаем.
3.  **Check Pool:** `MechanicsService` уже подготовил список доступных по цене финтов.
4.  **Buy Loop:**
    *   Пока есть свободные слоты и токены:
    *   Берем случайный финт из Пула.
    *   **Списываем токены** (Депозит).
    *   Генерируем короткий Хэш (ID карты).
    *   Сохраняем в Руку: `{hash: "abc12", feint_id: "heavy_hit", cost_paid: {...}}`.
5.  **Inject:** Вставляем кнопки (База + Рука) в `target.available_actions`.

---

## 4. Поток Данных (Data Flow)

### Фаза 1: Расчет (Mechanics -> Pool)
*   В конце хода обновляем `actor:pool` (список ID финтов, на которые *хватает* денег).

### Фаза 2: Отображение (View -> Hand)
*   `FeintService.fill_hand(actor)`: Докупает финты, если есть место и деньги.
*   `ViewService`:
    *   Рисует кнопку Базы (Label из конфига оружия).
    *   Рисует кнопки Финтов (Label из конфига финтов).
    *   Упаковывает всё в `target.available_actions`.

### Фаза 3: Исполнение (TurnManager -> Action)
*   **Если База:** Пропускаем (валидация оружия).
*   **Если Финт:**
    *   Ищем Хэш в Руке.
    *   Если найден -> Удаляем из Руки (карта сыграна).
    *   Если не найден -> Ошибка.

---

## 5. Важные Детали

*   **Смена Оружия:** В бою невозможна.
*   **Сброс Руки:** Не предусмотрен. Карты живут, пока не будут сыграны.
*   **Отображение Токенов:** Опционально (можно скрыть).
