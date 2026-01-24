# Login API (Resume Session)

## Status: ОТДЕЛЬНАЯ ЗАДАЧА

**Примечание:** Login и Resume Session - это ОТДЕЛЬНАЯ ЗАДАЧА, которая будет реализована позже.

Сейчас документируются только:
- Registration (User Upsert)
- Lobby (Character CRUD)

---

## Planned Features (FUTURE)

### Login Endpoint

**`POST /account/login`**

Восстановление игровой сессии персонажа (Resume Session).

#### Flow (Planned)

1. Чтение `ac:{char_id}` из Redis
2. Определение активного домена (Combat, Exploration, Scenario)
3. Вызов Context Assembler для подготовки данных
4. Вызов System Dispatcher для маршрутизации
5. Возврат CoreResponseDTO с entry point

---

## Dependencies (Not Ready)

- Context Assembler - подготовка domain session данных
- System Dispatcher - маршрутизация в активный домен
- RedisJSON - для работы с `ac:{char_id}`

---

## См. также

- [Roadmap](../Roadmap/README.md) - Phase 5: Login & Resume Session
- [Manifest.md](../Manifest.md) - раздел "Login (Resume Session) - ОТДЕЛЬНАЯ ЗАДАЧА"
