# 📅 Game Menu Roadmap

⬅️ [Back to Game Menu](./README.md)

## 🟢 Phase 1: Design & Documentation (Completed)
- [x] **Architecture:** Manifest, API, Gateway, Service, Client.
- [x] **Data Layer:** DTO (`AccountContextDTO`), Resources.
- [x] **Regen Logic:** Utility `regen.py` created.
- [x] **Session Handling:** Defined `SessionExpired` flow.

## 🟡 Phase 2: Backend Implementation
- [ ] **Shared DTO:** Create `GameMenuDTO` in `common/schemas/game_menu.py` (Shared between Backend & Client).
- [ ] **Session Service:** Implement `MenuSessionService` (Redis read + Lazy Regen + Validation).
- [ ] **Domain Service:** Implement `GameMenuService` (Assembly + Routing).
- [ ] **Gateway:** Implement `GameMenuGateway` (Response Wrapping).
- [ ] **Router:** Implement `GameMenuRouter` (FastAPI endpoints).
- [ ] **DI:** Register services in `backend/dependencies/features/game_menu.py` (or similar).

## 🔴 Phase 3: Client Implementation (Telegram Bot)
- [ ] **MenuClient:** Implement `MenuClient` (HTTP requests using Shared DTO).
- [ ] **MenuUI:** Implement `MenuUI` (Text formatting + Keyboard generation).
- [ ] **MenuOrchestrator:** Implement `MenuBotOrchestrator` (Logic + State Switching).
- [ ] **Handlers:** Implement `menu_handlers.py`.
- [ ] **DI:** Register client/orchestrator in `AppContainer`.
- [ ] **Integration:** Replace legacy `MenuService` usage in `menu_dispatch.py`.

## 🟣 Phase 4: Cleanup & Testing
- [ ] **Remove Legacy:** Delete `game_client/bot/ui_service/mesage_menu`.
- [ ] **Testing:** Verify Regen logic, Session Expiry flow, and Navigation.
