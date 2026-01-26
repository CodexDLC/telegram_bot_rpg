# 📂 Account Roadmap

[⬅️ Назад: Account Domain](../README.md)

---

## Текущий статус

**Phase:** ✅ Implementation DONE (MVP 0.1.0)

**Refactoring:** Объединение Auth + Lobby + Onboarding в единый Account Domain - **ЗАВЕРШЕНО**.

---

## Что СДЕЛАНО (MVP 0.1.0)

### ✅ Phase 0: Documentation
- [x] Manifest.md
- [x] API спецификация (Registration, Lobby, Onboarding, Login)
- [x] Gateway & Services documentation
- [x] Roadmap

### ✅ Phase 1: Data Layer
- [x] DTOs созданы в `common/schemas/`
- [x] CharactersRepoORM реализован
- [x] AccountManager с RedisJSON
- [x] Lobby Cache-Aside

### ✅ Phase 2: Backend API & Services
- [x] RegistrationGateway & RegistrationService
- [x] LobbyGateway & LobbyService (Cache-Aside)
- [x] OnboardingGateway & OnboardingService (Wizard Flow)
- [x] LoginGateway & LoginService (Resume Session)
- [x] AccountSessionService (центральный сервис для ac:{char_id})
- [x] API Endpoints:
  - `POST /account/register`
  - `POST /account/lobby/{user_id}/initialize`
  - `GET /account/lobby/{user_id}/characters`
  - `POST /account/lobby/{user_id}/characters`
  - `DELETE /account/lobby/characters/{char_id}`
  - `POST /account/onboarding/{char_id}/action`
  - `POST /account/lobby/{user_id}/characters/{char_id}/login`

### ✅ Phase 3: Bot Client Migration
**Цель:** Обновить Telegram Bot для использования новых сервисов.

**HTTP Client / Gateway Access:**
- [x] `AccountClient` (обертка над HTTP API)
- [x] `StartBotOrchestrator`
- [x] `LobbyOrchestrator`
- [x] `OnboardingOrchestrator`
- [x] Handlers & UI Components

**Cleanup:**
- [x] Удален легаси код (`apps/game_core/...`)

---

## TODO (Post-MVP)

### Phase 4: Testing
**Цель:** Стабилизация и покрытие тестами.

- [ ] **[Task: Testing Plan](./Task_Testing_Plan.md)** — Выполнение плана тестирования (Unit, Integration, E2E).

---

### Phase 5: Domain Integration (Finalize)
**Цель:** Подключение всех отрефакторенных доменов к единой системе аккаунта.

- [ ] **Scenario Integration:**
  - [ ] `OnboardingService.finalize()` -> Переход в Scenario (Intro Quest).
  - [ ] Обновление `game_stage` в БД при завершении онбординга.
- [ ] **Persistence:**
  - [ ] ARQ Worker для асинхронного сохранения данных из Redis (`ac:{char_id}`) в PostgreSQL.
- [ ] **Routing:**
  - [ ] Настройка `LoginService` для корректного перехода в Combat/Exploration.

---

### Phase 6: Logout & Cleanup (FUTURE)
**Цель:** Реализовать корректный выход из игры.

- [ ] `POST /account/logout` endpoint
- [ ] Сохранение состояния из `ac:{char_id}` в БД
- [ ] Очистка временных сессий
