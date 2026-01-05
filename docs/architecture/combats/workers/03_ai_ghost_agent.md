# AI Ghost Agent (The Bot) Specification

**Role:** NPC Logic Executor.
**Responsibility:** Принятие решений за мобов и AFK-игроков.

---

## 1. Workflow

### A. Trigger
Запускается Коллектором (`combat_collector_task`), если обнаружено, что бот не сделал ход (или не покрыл все цели в очереди).
Задача: `AiTurnRequestDTO(session_id, bot_id, missing_targets)`.

### B. Context Loading (Optimized)
В отличие от старой версии, AI Worker **не загружает** тяжелый контекст боя (Meta, Actors).
Он получает список обязательных целей (`missing_targets`) прямо в задаче от Коллектора.
Это минимизирует чтения из Redis.

### C. Decision Making (AiProcessor)
Использует `AiProcessor` (в `processors/ai_processor.py`) для генерации решения.
*   **Target Selection:** Итерирует по списку `missing_targets`.
*   **Action Selection:** Пока использует базовую атаку ("exchange"). В будущем будет выбирать скиллы.
*   **Zone Selection:** Рандомно выбирает зоны атаки (1 зона) и защиты (2 соседние зоны).

### D. Move Registration (Batch)
Использует `CombatTurnManager.register_moves_batch`:
1.  Собирает все решения в список `payloads`.
2.  Отправляет их одним вызовом.
3.  `TurnManager` валидирует, пишет в Redis (атомарно с удалением целей из очереди) и отправляет **один** сигнал Коллектору.

---

## 2. Key Features

*   **Stateless:** Бот не хранит состояние между запусками.
*   **Reactive:** Бот реагирует на "дыры" в очереди целей.
*   **Batch Processing:** Бот делает все ходы за один раз (Spamming Intents).
*   **Atomic:** Регистрация ходов гарантирует, что цели удаляются из очереди, предотвращая зацикливание.
