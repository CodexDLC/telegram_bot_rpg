# План рефакторинга перед разделением на контейнеры (Pre-Docker/Postgres)

**Статус:** Отложено до этапа MVP / Внедрения Postgres.
**Цель:** Устранить прямые зависимости между `Bot Layer` и `Game Core Layer` для обеспечения работы через API Gateway.

## 1. UI Services (Слой представления)

### A. MenuService (`apps/bot/ui_service/menu_service.py`)
* **Проблема:** Импортирует `GameSyncService` для регенерации HP/Energy при отрисовке.
* **Решение:**
    * Вынести регенерацию в фоновый процесс (Celery/Cron/System Ticks), который крутится в отдельном контейнере.
    * Меню должно только *читать* текущее состояние из Redis, не инициируя расчеты.

### B. NavigationService (`apps/bot/ui_service/navigation_service.py`)
* **Проблема:** Импортирует `GameWorldService` и напрямую пишет в Redis (перемещение).
* **Решение:**
    * Разделить `GameWorldService` на два интерфейса/класса:
        1.  **Reader (UI):** Только чтение графа мира из Redis для отрисовки.
        2.  **Mutator (Core):** Валидация и изменение координат игрока.
    * UI сервис будет дергать Mutator через API (или внутренний роут), а данные для отрисовки брать через Reader.

### C. CombatUIService (`apps/bot/ui_service/combat/combat_ui_service.py`)
* **Проблема:** Импортирует `StatsCalculator` (Core) для расчета Max HP.
* **Решение:**
    * Создать Фасад (Facade) в `CombatService` или Helper-сервисе, который отдает готовые DTO с уже посчитанными статами.
    * UI не должен знать формулы расчета статов.

## 2. Handlers (Точки входа)

**Файлы:**
* `apps/bot/handlers/callback/login/login_handler.py`
* `apps/bot/handlers/callback/ui/menu_dispatch.py`
* `apps/bot/handlers/callback/game/combat/action_handlers.py`

* **Проблема:** "God Handlers". Они напрямую импортируют сервисы ядра (`LoginService`, `CombatService`, `GameSyncService`) и управляют логикой.
* **Решение:**
    * Переписать хендлеры так, чтобы они обращались к Ядру только через единый интерфейс (в будущем — HTTP Client к FastAPI).
    * Убрать логику оркестрации из хендлеров, оставив там только вызов метода и передачу результата в UI.