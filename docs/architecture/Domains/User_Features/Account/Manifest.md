# Account Domain - Manifest

## Назначение Домена

**Account Domain** отвечает за управление учетными записями пользователей, персонажами (Lobby) и процессом входа в игру (Login/Onboarding).

Это ПЕРЕНОС и РЕФАКТОРИНГ функциональности:
- `apps/game_core/modules/auth/` → полная переработка (legacy Auth - херня)
- `apps/game_core/modules/lobby/` → перенос as-is (хорошие паттерны, Cache-Aside)
- `apps/game_core/modules/onboarding/` → интеграция внутрь Account Domain (как sub-feature)

## Основные Обязанности

### 1. Registration (Регистрация)
- User Upsert (создание/обновление записи пользователя)
- Первичная инициализация данных
- Прямой доступ к БД (исключение из правила)

### 2. Lobby (Управление персонажами)
- Список персонажей (до 4 штук)
- Создание Character Shell (пустая запись для Onboarding)
- Удаление персонажей
- Cache-Aside паттерн (Redis + PostgreSQL)

### 3. Onboarding (Создание персонажа)
- Инициализация контекста `ac:{char_id}`
- Wizard flow (заполнение имени, пола)
- Финализация (переход в Scenario) - ⚠️ TODO

### 5. Account Session Management (AccountSessionService)
- Создание `ac:{char_id}` из CharacterReadDTO
- Получение/обновление `ac:{char_id}` (state, bio, stats, sessions)
- Управление кэшем лобби (lobby:user:{user_id})
- Центральная точка для работы с AccountContextDTO

### 4. Login (Resume Session)
- Проверка/Восстановление контекста `ac:{char_id}`
- Маршрутизация по полю `state` (ONBOARDING, COMBAT, SCENARIO, EXPLORATION)
- State field - единственный источник истины для определения текущего домена

## Границы Ответственности

### В ЗОНЕ ОТВЕТСТВЕННОСТИ:
- ✅ User CRUD
- ✅ Character CRUD (включая Shell)
- ✅ Список персонажей (Lobby UI)
- ✅ Кеширование списка персонажей
- ✅ Инициализация и восстановление `ac:{char_id}`
- ✅ Onboarding Flow (внутри домена)
- ✅ Login Routing (определение куда пустить игрока)

### ВНЕ ЗОНЫ ОТВЕТСТВЕННОСТИ:
- ❌ Управление инвентарем (Inventory Domain)
- ❌ Боевая система (Combat Domain)
- ❌ Исследование мира (Exploration Domain)
- ❌ Рендер UI других доменов (только делегирование через Dispatcher)

## Структура Домена

```
backend/domains/user_features/account/
├── api/
│   └── router.py                    # FastAPI endpoints
├── gateway/
│   ├── registration_gateway.py      # Registration Gateway
│   ├── lobby_gateway.py             # Lobby Gateway
│   ├── onboarding_gateway.py        # Onboarding Gateway (Wizard Flow)
│   └── login_gateway.py             # Login Gateway (Resume Session)
├── services/
│   ├── registration_service.py      # User Upsert бизнес-логика
│   ├── lobby_service.py             # Character CRUD + Cache-Aside
│   ├── onboarding_service.py        # Wizard Flow (Onboarding)
│   ├── login_service.py             # Восстанавливает ac:{char_id}
│   └── account_session_service.py   # ⭐ ЦЕНТРАЛЬНЫЙ сервис для ac:{char_id}
├── dto/
│   ├── registration.py              # UserUpsertDTO
│   ├── lobby.py                     # LobbyListDTO, CharacterShellDTO
│   ├── onboarding.py                # OnboardingViewDTO
│   └── payloads.py                  # Request/Response models
└── README.md
```

## Gateway Pattern

Account Domain использует Gateway Layer как посредник между API и Services.
(См. Gateway/README.md для деталей).

## Взаимодействие с другими компонентами

### 1. Telegram Bot Client
- Bot делает HTTP запросы к Account API.
- Получает CoreResponseDTO.

### 2. Database (Прямой доступ)
- **Таблицы:** `users`, `characters`
- **Redis:** Cache-Aside для Lobby (`lobby:user:{user_id}`)
- **RedisJSON:** Active Context (`ac:{char_id}`)

### 3. System Dispatcher
- Маршрутизация Resume Session в активный домен.

## Ключевые Особенности

### Cache-Aside Pattern (Lobby)
**Переносится AS-IS из legacy Lobby (хорошая реализация)**
- Read: Redis -> DB -> Redis (TTL 1h)
- Write: DB -> Invalidate Redis

### Smart JSON (Onboarding & Login)
- Используется RedisJSON для `ac:{char_id}`.
- Позволяет точечно обновлять поля (например, `.bio.name`) без перезаписи всего объекта.

### Flows

#### Create Character (Lobby → Onboarding)
1. `LobbyService.create_character_shell()` создает Character Shell в БД (+ CharacterAttributes, CharacterSymbiote, ResourceWallet с дефолтами).
2. **ПРЯМОЙ вызов** `OnboardingService.initialize(character)` (тот же домен).
3. `OnboardingService` создает `ac:{char_id}` через `AccountSessionService` со `state=ONBOARDING`.
4. Возвращает `OnboardingUIPayloadDTO` (первый шаг: NAME).
5. `LobbyGateway` оборачивает в `CoreResponseDTO` с `current_state=ONBOARDING`.

#### Login / Resume (Login → Onboarding/Other Domains)
1. `LoginService` проверяет наличие `ac:{char_id}`.
2. Если нет → Восстанавливает из БД через `AccountSessionService.create_session()`.
3. Читает `state` из `ac:{char_id}`.
4. `LoginGateway` маршрутизирует:
   - Если `state=ONBOARDING` → **ПРЯМОЙ вызов** `OnboardingGateway.resume(char_id)` (тот же домен)
   - Если `state=COMBAT/SCENARIO/EXPLORATION` → Через `SystemDispatcher.route(domain, "resume", context)`
5. Возвращает `CoreResponseDTO` с entry point целевого домена.

## Database Changes

### Table: characters
**Добавить поля:**
```sql
-- Снимок текущих HP/MP/Stamina для быстрого доступа
vitals_snapshot JSONB DEFAULT '{
  "hp": {"cur": 100, "max": 100},
  "mp": {"cur": 50, "max": 50},
  "stamina": {"cur": 100, "max": 100}
}'::jsonb;

-- Список активных сессий персонажа
active_sessions JSONB DEFAULT '{
  "combat_session_id": null,
  "inventory_session_id": null,
  "scenario_session_id": null
}'::jsonb;
```

## Миграция с Legacy

### Что ПЕРЕНОСИМ (TRANSFER/REFACTOR):
- ✅ `lobby_orchestrator.py` → `lobby_gateway.py` + `lobby_service.py`
- ✅ `lobby_session_manager.py` → Cache-Aside в `lobby_service.py`
- ✅ `onboarding` → `onboarding_service.py` + `onboarding_gateway.py`

### Что НЕ переносим:
- ❌ Legacy Auth логика
- ❌ Onboarding костыли (char_id/user_id путаница) - ИСПРАВЛЕНО в новой архитектуре.

## Зависимости

### Required:
- PostgreSQL
- Redis (RedisJSON для `ac:`)
- FastAPI
- System Dispatcher
