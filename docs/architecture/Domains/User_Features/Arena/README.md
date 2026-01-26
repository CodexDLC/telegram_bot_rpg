# 📂 Arena Domain (Арена)

[⬅️ Назад: User Features](../README.md) | [🏠 Root](../../../../README.md)

---

## 🎯 Цель домена
Организация PvP-боев, матчмейкинг, управление очередями и рейтингами.

## 🗺️ Содержание

### 🏗️ Основные файлы
* [📄 Manifest.md](./Manifest.md) — Паспорт и границы ответственности.
* [📄 Roadmap.md](./Roadmap.md) — Главный план развития (Checklist).

### 📂 Слои Архитектуры
* [**API/**](./API/README.md) — Входные точки и контракты.
* [**Backend/**](./Backend/README.md) — Сервисы и бизнес-логика.
* [**Client/**](./Client/README.md) — Telegram клиент и UI.
* [**Data/**](./Data/README.md) — DTO, Redis и Enums.
* [**Migration/**](./Migration/README.md) — План миграции.
* [**Tests/**](./Tests/README.md) — Тестирование.

### 📝 Задачи развития (Tasks)
* [📄 Task_WebSocket.md](./Tasks/Task_WebSocket.md) — Внедрение WebSocket.
* [📄 Task_GearScore.md](./Tasks/Task_GearScore.md) — Расчет GearScore.
* [📄 Task_NewModes.md](./Tasks/Task_NewModes.md) — Новые режимы (Group, Tournament).

---

## ⚠️ Правила домена
*   Соблюдать Clean Architecture.
*   Все изменения фиксировать в Changelog (TODO).