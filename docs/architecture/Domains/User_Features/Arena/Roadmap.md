# 🗺️ Arena Roadmap

[⬅️ Назад: Arena Domain](./README.md)

## 🤖 AI CONTEXT
Главный чек-лист развития домена. Детальные описания задач вынесены в отдельные файлы в папке `Tasks/`.

## 📊 Фазы развития

### Phase 1: MVP (Current)
- [ ] **Backend API** (Единый action endpoint)
- [ ] **ArenaGateway** (Роутинг + `CoreResponseDTO`)
- [ ] **ArenaService** (Бизнес-логика матчмейкинга)
- [ ] **ArenaSessionManager** (Инкапсуляция Redis managers)
- [ ] **Client Orchestrator** (Координация + polling)
- [ ] **Client Handler** (Единый handler)
- [ ] **Polling Animation** (`UIAnimationService` интеграция)
- [ ] **Режим 1v1** (Полный flow)
- [ ] **GearScore Stub** (Константа 100)

### Phase 2: Post-MVP Improvements
- [ ] [**GearScore Calculation**](./Tasks/Task_GearScore.md) — Реальный расчёт GS.
- [ ] **Match History** — Сохранение истории через ARQ worker.
- [ ] **Leaderboard** — Рейтинг игроков арены.
- [ ] **Statistics** — Win/Loss ratio, streak.

### Phase 3: New Modes
- [ ] [**New Modes Implementation**](./Tasks/Task_NewModes.md) — Group, Tournament, Ranked.

### Phase 4: Real-time
- [ ] [**WebSocket Integration**](./Tasks/Task_WebSocket.md) — Переход на WS.

## 📋 Tech Debt
- [ ] **Error Handling** — Полная обработка edge cases.
- [ ] **Tests** — Unit + Integration тесты.
- [ ] **Metrics** — Prometheus метрики.