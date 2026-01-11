# ⚡ Redis Infrastructure

⬅️ [Назад](../README.md)

Документация по архитектуре работы с Redis.

## 1. Architecture Layers (Слои Абстракции)

Мы используем многослойную архитектуру для работы с Redis, чтобы изолировать бизнес-логику от низкоуровневых команд.

### Layer 1: Key Registry (`redis_key.py`)
Централизованное хранилище паттернов ключей.
*   **Документация:** [Key Schema Registry](./key_schema.md).

### Layer 2: Field Registry (`redis_fields.py`)
Хранилище имен полей для HASH-структур.

### Layer 3: Redis Service (`redis_service.py`)
Низкоуровневая обертка над драйвером `redis-py`.

### Layer 4: Domain Managers (`*_manager.py`)
Высокоуровневые сервисы, реализующие бизнес-операции.
*   **Документация:** [Managers Registry](./managers.md).

---

## 2. Data Structures Strategy

### JSON vs Hash
*   **RedisJSON (`ReJSON`):** Используется для сложных вложенных структур (очереди целей, логи, инвентарь).
*   **RedisHash:** Используется для плоских структур с частым доступом к отдельным полям (HP, Energy, State).

### Pipelines
Все операции, затрагивающие несколько ключей, **обязаны** выполняться внутри `pipeline`.

---

## 3. ARQ (Async Redis Queue)
Для фоновых задач используется библиотека `arq`.
*   **Очереди:** `combat_queue`, `system_queue`.
