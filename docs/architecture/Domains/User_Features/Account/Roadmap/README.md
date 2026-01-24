# Account Domain - Roadmap

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

---

## TODO (Post-MVP)

### Phase 3: Bot Client Migration

**Цель:** Обновить Telegram Bot для использования новых сервисов.

**HTTP Client / Gateway Access:**
- [ ] `AccountClient` (обертка над HTTP API)
  - [ ] `register_user`
  - [ ] `initialize_lobby`
  - [ ] `list_characters`, `create_character`, `delete_character`
  - [ ] `login`
  - [ ] `onboarding_action`

**Bot Orchestrators:**
- [ ] `StartBotOrchestrator` → использует AccountClient
- [ ] `LobbyBotOrchestrator` → использует AccountClient
- [ ] `OnboardingBotOrchestrator` → использует AccountClient

**Handlers:**
- [ ] Обновить хендлеры `/start`, Lobby, Onboarding
- [ ] FSM states для Onboarding

**Cleanup:**
- [ ] Удалить `apps/game_core/modules/auth/`
- [ ] Удалить `apps/game_core/modules/lobby/`
- [ ] Удалить `apps/game_core/modules/onboarding/`

---

### Phase 4: Testing

**Цель:** Полное тестирование всех потоков.

**Unit Tests:**
- [ ] Services tests (Registration, Lobby, Onboarding, Login, AccountSessionService)
- [ ] Gateway tests
- [ ] Repository tests

**Integration Tests:**
- [ ] Full flow: Register → Initialize Lobby → Create Character → Onboarding → Login
- [ ] Cache invalidation tests
- [ ] RedisJSON updates tests

**E2E Tests:**
- [ ] Bot → HTTP API → PostgreSQL + Redis
- [ ] Character limit (4 персонажа)
- [ ] Ownership validation (403 на чужого персонажа)

---

### Phase 5: Finalize Implementation (Зависит от Scenario Domain)

**Цель:** Завершить недоделанные части.

- [ ] `OnboardingService.finalize()` - переход в Scenario
- [ ] ARQ Worker для сохранения данных из Redis в БД
- [ ] Scenario Domain интеграция (интро сценарий)
- [ ] Update `game_stage` в БД при finalize

---

### Phase 6: Logout & Cleanup (FUTURE)

**Цель:** Реализовать корректный выход из игры.

- [ ] `POST /account/logout` endpoint
- [ ] Сохранение состояния из `ac:{char_id}` в БД
- [ ] Очистка временных сессий

---

## Success Criteria (MVP 0.1.0) - ✅ DONE

- [x] Registration работает
- [x] Lobby работает (Initialize + CRUD + Cache)
- [x] Onboarding работает (Wizard + RedisJSON) **Кроме finalize - зависит от Scenario**
- [x] Login работает (Resume Session + Routing)
- [x] AccountSessionService работает (центральный сервис для ac:{char_id})
- [ ] Старый код удален (Phase 3 - Bot Migration)

---

## Примечания

- **finalize() - TODO:** Зависит от миграции Scenario Domain и создания ARQ Worker для сохранения в БД
- **Post-MVP Tasks:** Все задачи выше Phase 3 - для версий после 0.1.0
- **Current Focus:** Миграция других доменов (Combat, Scenario, Exploration) для полной интеграции
