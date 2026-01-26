# 📂 Account Domain

[⬅️ Назад: User Features](../README.md) | [🏠 Root](../../../../README.md)

---

## 🎯 Цель домена
Управление жизненным циклом пользователей и персонажей:
- Регистрация Telegram пользователей.
- Управление персонажами (Lobby: создание, удаление, выбор).
- Вход в игру с восстановлением последней сессии (Login + Resume Session).

Это **единая точка входа** игрока в систему.

## 🗺️ Содержание

### 🏗️ Основные файлы
* [📄 00_Manifest.md](./Manifest.md) — Паспорт и границы ответственности.
* [📄 01_Roadmap.md](./Roadmap/README.md) — Текущие задачи и план рефакторинга.
* [📄 Changelog.md](./Changelog.md) — История изменений.

### 🧩 Слои Архитектуры
| Слой | Папка | Описание |
| :--- | :--- | :--- |
| **View** | [📂 Client_Interface](./Client_Interface/README.md) | Интеграция с Telegram ботом. |
| **API** | [📂 API](./API/README.md) | Спецификация HTTP Endpoints. |
| **Gateway** | [📂 Gateway](./Gateway/README.md) | Точки входа в бизнес-логику. |
| **Service** | [📂 Services](./Services/README.md) | Логика (Registration, Lobby, Login). |
| **Data** | [📂 Data](./Data/README.md) | DTOs и модели данных. |

---

## ⚙️ Архитектурные слои

```
┌─────────────────────────────────────────┐
│  Client (Telegram Bot)                  │
│  ├─ /start → Registration               │
│  ├─ Select Character → Login            │
│  └─ Lobby Menu → Lobby Actions          │
└─────────────────┬───────────────────────┘
                  │ HTTP API
┌─────────────────▼───────────────────────┐
│  API Layer (FastAPI Endpoints)          │
│  ├─ POST /account/register              │
│  ├─ POST /account/lobby/initialize      │
│  ├─ POST /account/login                 │
│  └─ DELETE /account/characters/{id}     │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│  Gateway Layer                          │
│  └─ AccountGateway                      │
│     ├─ Координация между сервисами      │
│     └─ Вызов Dispatcher для роутинга    │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│  Service Layer                          │
│  ├─ RegistrationService                 │
│  ├─ LobbyService (Cache-Aside)          │
│  └─ LoginService (Resume Session)       │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│  Data Layer                             │
│  ├─ UsersRepoORM (PostgreSQL)           │
│  ├─ CharactersRepoORM (PostgreSQL)      │
│  └─ AccountManager (Redis)              │
└─────────────────────────────────────────┘
```

---

## 🔗 Интеграции

### → Context Assembler
Login Service вызывает Context Assembler для подготовки доменной сессии в Redis.

### → System Dispatcher
Login Service передаёт управление Dispatcher, который возвращает view для UI.

### → Onboarding Domain
Lobby перенаправляет на Onboarding если у пользователя нет персонажей.
