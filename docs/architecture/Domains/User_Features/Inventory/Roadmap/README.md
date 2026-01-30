# 🗺️ Inventory Domain Roadmap

[⬅️ Назад: Inventory Domain](../README.md)

---

## 🎯 Текущий Статус
**Active Phase:** Migration to Session-Based Architecture & Composite UI.

Мы переходим от концептуального проектирования к реализации ядра инвентаря на базе RedisJSON и обновленной клиентской архитектуры.

---

## 📋 Active Tasks

### 1. 🟡 Session & Composite Migration
**Подробности:** [Task_Session_Migration.md](./Task_Session_Migration.md)
*   Внедрение `CoreCompositeResponseDTO`.
*   Обновление `BaseBotOrchestrator`.
*   Реализация `InventorySessionManager` (Redis).
*   Реализация `InventoryGateway` и `Service`.

### 2. ⚪ Item Effects Integration (Future)
*   Интеграция с `EffectsEngine` через `DispatcherBridge`.
*   Реализация использования расходников (Consumables).

### 3. ⚪ Database Synchronization (Future)
*   Реализация фонового воркера для сохранения `dirty` сессий из Redis в PostgreSQL.

---

## ✅ Completed Tasks
*   [x] Архитектурный манифест (Manifest.md).
*   [x] Проектирование API Routes.
*   [x] Проектирование структуры данных (Redis Schema).
*   [x] Проектирование клиентских интерфейсов (Telegram).
