# Стандарт разработки хендлеров и UI (v2.0: Orchestrator Pattern)

## 1. Архитектурная философия
Проект строится на строгом разделении ответственности между слоями. Мы используем паттерн **Orchestrator** для изоляции бизнес-логики от Telegram-интерфейса.

### Цепочка вызовов (Data Flow)
`Handler` -> `Bot Orchestrator` -> `Core Client` -> `Core Orchestrator` -> `Domain Service`

1.  **Handler (UI Controller)**:
    *   **Роль**: Принимает `CallbackQuery`, достает данные из FSM, вызывает `Bot Orchestrator`.
    *   **Запрещено**: Бизнес-логика, прямые вызовы БД, ручное формирование клавиатур.
    *   **Пример**: `inventory_main.py`

2.  **Bot Orchestrator (UI Logic)**:
    *   **Роль**: Преобразует данные из Core в UI-формат (DTO). Управляет состоянием интерфейса (какое меню показать).
    *   **Инструменты**: Использует `UIService` для рендеринга и `Core Client` для данных.
    *   **Пример**: `InventoryBotOrchestrator`

3.  **Core Client (Gateway/Adapter)**:
    *   **Роль**: Адаптер для общения с Ядром. В будущем это будет gRPC/HTTP клиент. Сейчас это обертка над `Core Orchestrator`.
    *   **Пример**: `InventoryClient`

4.  **Core Orchestrator (Business Facade)**:
    *   **Роль**: Единая точка входа в бизнес-логику модуля. Агрегирует вызовы к разным сервисам (Инвентарь + Кошелек + Статистика).
    *   **Пример**: `InventoryCoreOrchestrator`

5.  **Domain Service (Business Logic)**:
    *   **Роль**: Чистая логика игры. Работает с БД и Redis.
    *   **Пример**: `InventoryService`

---

## 2. Стандарты данных (DTO)
Мы отказываемся от передачи "сырых" данных (кортежей, словарей) между слоями.

*   **ViewDTO**: Все методы UI-слоя возвращают типизированные объекты (например, `InventoryViewDTO`), содержащие текст, клавиатуру и метаданные.
*   **MessageCoordsDTO**: Для передачи координат сообщения (`chat_id`, `message_id`) используется DTO, а не кортеж/индексы.

## 3. Роли сообщений (Dual-Message System)
Интерфейс игрока всегда состоит из двух сообщений. Смешивание их ролей запрещено.

*   **message_content (Верхнее):** «Дашборд». Карта локации, статус участников боя, описание NPC.
*   **message_menu (Нижнее):** «Органы управления». Кнопки перемещения, инвентарь, быстрые слоты, лог боя.

## 4. Правила рендеринга
*   **Запрет на `call.message.edit_text`:** Использование `call.message` внутри бизнес-логики хендлера запрещено.
*   **ID из Orchestrator:** Хендлер получает координаты сообщений через методы оркестратора (`get_content_coords`, `get_menu_coords`).
*   **Анимации:** Длительные операции сопровождаются вызовом `UIAnimationService`.

## 5. Разделение данных (FSM vs Redis)
*   **FSM (Контекст бота):** Хранит только UI-контекст (ID сообщений, текущая страница, выбранный фильтр).
*   **Redis (Ядро):** Единственный источник правды для игрового состояния.

## 6. Универсальные переходы
Любая смена режима игры (выход из боя, вход в сервис) выполняется через `HubEntryService` или методы оркестратора (`leave_combat`, `leave_arena`), которые возвращают `new_state`.

## 7. Обработка ошибок
Каждый хендлер обязан иметь блок `try/except`.
При возникновении ошибки: `log.exception` и `Err.report_and_restart(call)`.

---

## Пример реализации (Inventory)

### Handler
```python
@router.callback_query(...)
async def handler(call, state, container, session):
    orchestrator = container.get_inventory_bot_orchestrator(session)
    result = await orchestrator.get_main_menu(...)
    
    if coords := orchestrator.get_content_coords(...):
        await bot.edit_message_text(..., text=result.content.text, reply_markup=result.content.kb)
```

### Bot Orchestrator
```python
class InventoryBotOrchestrator:
    async def get_main_menu(self, ...):
        data = await self.client.get_summary(...)
        view = self.ui.render_main_menu(data)
        return InventoryViewDTO(content=view)
```
