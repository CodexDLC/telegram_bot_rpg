# Account Domain - Changelog

## [Unreleased] - Documentation Phase

### Added
- Complete documentation structure for Account Domain
- Manifest.md - domain description and responsibilities
- README.md - overview and architecture diagrams
- API documentation:
  - Registration API (POST /account/register)
  - Lobby API (initialize, list, create, delete characters)
  - Login API (Resume Session через Dispatcher)
- Data models documentation (DTOs, Redis structures, DB tables)
- Client Interface documentation (Telegram Bot integration)
- Orchestrator Layer documentation (services and business logic)
- Roadmap with detailed implementation phases

### Planned
- Phase 1: Data Layer Migration (DTOs to common/schemas)
- Phase 2: Backend API Implementation (FastAPI endpoints)
- Phase 3: Context Assembler Integration
- Phase 4: System Dispatcher Integration (Resume Session)
- Phase 5: Bot Client Migration (HTTP API instead of direct DB access)
- Phase 6: Testing & Refinement
- Phase 7: Logout & Cleanup

---

## Future Versions

### [0.1.0] - Initial Implementation
**Target:** Basic Account Domain без Resume Session

- [ ] Registration API
- [ ] Lobby API (list/create/delete)
- [ ] Basic Login (без Resume Session)
- [ ] Bot integration

### [0.2.0] - Resume Session
**Target:** Полноценный Resume Session через Dispatcher

- [ ] Context Assembler integration
- [ ] System Dispatcher integration
- [ ] Resume для Combat
- [ ] Resume для Exploration

### [0.3.0] - Polish & Features
**Target:** Улучшения и дополнительные фичи

- [ ] Logout with state persistence
- [ ] Character slots limit
- [ ] Soft delete для персонажей
- [ ] Performance optimization
- [ ] Analytics & metrics

---

## Migration Notes

### From Legacy Auth + Lobby

**Old structure:**
```
apps/game_core/modules/auth/
apps/game_core/modules/lobby/
```

**New structure:**
```
backend/domains/user_features/account/
```

**Key changes:**
- Unified domain instead of separate modules
- HTTP API instead of direct DB access from bot
- Resume Session через System Dispatcher
- Cache-Aside паттерн для Lobby
- Integration with Context Assembler

---

## Breaking Changes (Planned)

### Bot Client
- AuthClient: direct DB access → HTTP API
- LobbyOrchestrator: legacy structure → new API calls
- FSM states: могут измениться (BotState.lobby)

### Backend
- Удаление legacy `apps/game_core/modules/auth/`
- Удаление legacy `apps/game_core/modules/lobby/`
- Новые DTO в `common/schemas/`

---

## Version History

### 2025-01-24 - Documentation Created
- Initial documentation structure
- API specification (Registration, Lobby)
- Integration guidelines
- Gateway pattern architecture
- Roadmap created (простой чеклист без оценок времени)
- Login marked as FUTURE (отдельная задача)
