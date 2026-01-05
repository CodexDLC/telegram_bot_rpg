# Combat Initialization Flow

Этот документ описывает процесс инициализации боевой сессии, структуру входных данных и порядок действий оркестратора.

## 1. Входные данные (Caller -> Orchestrator)

Инициализация боя происходит через метод `CombatEntryOrchestrator.initialize_combat`.
Вызывающий сервис должен передать контекст инициализации `CombatInitContextDTO`.

### Структура DTO

```python
class CombatTeamDTO(BaseModel):
    """
    Описание одной команды.
    """
    players: list[int] = []       # Список ID игроков (char_id)
    pets: list[int] = []          # Список ID питомцев (TODO)
    monsters: list[str] = []      # Список ключей/ID монстров (например, "orc_warrior")

class CombatInitContextDTO(BaseModel):
    """
    Контекст инициализации боя.
    """
    mode: str = "standard"        # Режим боя: "standard", "shadow", "arena", "dungeon"
    teams: list[CombatTeamDTO]    # Список команд (индекс в списке определяет команду)
```

### Пример JSON

```json
{
    "mode": "standard",
    "teams": [
        {
            "players": [101, 102],
            "pets": [],
            "monsters": []
        },
        {
            "players": [],
            "monsters": ["orc_warrior", "orc_archer"]
        }
    ]
}
```

## 2. Логика Оркестратора (`CombatEntryOrchestrator`)

1.  **Создание сессии**: Генерируется уникальный `session_id` (UUID).
2.  **Создание записи боя**: Вызывается `lifecycle.create_battle` с параметрами режима.
3.  **Обработка команд**:
    *   Команды распределяются по цветам: `blue` (0), `red` (1), `green` (2), `yellow` (3).
    *   **Игроки**: Добавляются через `lifecycle.add_participant`. Имена подтягиваются из аккаунта.
    *   **Монстры**:
        *   Загружаются батчем через `MonsterRepository`.
        *   Каждому монстру присваивается уникальный **отрицательный ID** внутри сессии (начиная с -1), чтобы избежать коллизий с ID игроков.
        *   Добавляются через `lifecycle.add_db_monster_participant`.
4.  **Инициализация состояния**:
    *   `lifecycle.initialize_battle_state`: Расчет целей, зарядов тактики.
    *   `lifecycle.initialize_exchange_queues`: Наполнение очередей обмена ударами.
5.  **Возврат результата**:
    *   Возвращается `CoreResponseDTO` со снапшотом для первого игрока из списка.

## 3. Особенности ID участников

*   **Игроки**: Используют свой реальный `char_id` (положительное число).
*   **Монстры**: Получают временный отрицательный ID (`-1`, `-2`, ...). Это позволяет отличать их от игроков и гарантирует уникальность в рамках сессии, даже если монстры одного типа.
*   **Тени (Shadows)**: В режиме `shadow` клоны игроков также получают отрицательные ID (обычно `-original_char_id`).

## 4. Пример вызова

```python
context = CombatInitContextDTO(
    mode="dungeon",
    teams=[
        CombatTeamDTO(players=[user_char_id]),
        CombatTeamDTO(monsters=["boss_dragon"])
    ]
)
response = await orchestrator.initialize_combat(context)
```
