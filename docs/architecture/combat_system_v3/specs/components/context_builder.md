# Component: ContextBuilder

⬅️ [Назад](../README.md) | 🏠 [Документация](../../../../README.md)

**File:** `apps/game_core/modules/combat/combat_engine/logic/context_builder.py`
**Responsibility:** Фабрика контекста и Анализатор намерений.

## 1. Назначение
`ContextBuilder` выполняет две функции:
1.  **Analyzer (Pre-Executor):** Анализирует намерения участников **до** создания задач, чтобы выявить конфликты (Interference) и возможности (Dual Wield).
2.  **Builder (In-Pipeline):** Создает `PipelineContextDTO` для конкретного удара, применяя результаты анализа.

---

## 2. API Methods

### A. Analyze Exchange (Public, Static)
Вызывается `Executor`'ом перед созданием задач.

```python
def analyze_exchange(
    source: ActorSnapshot, 
    target: ActorSnapshot, 
    move_a: CombatMoveDTO, 
    move_b: CombatMoveDTO | None
) -> tuple[dict, dict]:
```

**Логика:**
1.  **Interference Check:**
    *   Проверяет `active_abilities` на наличие контроля (Stun, Sleep).
    *   Если есть контроль -> `mods["disable_attack"] = True`.
    *   Сравнивает инициативу (если нужно для прерывания).
2.  **Dual Wield Check:**
    *   Проверяет `loadout` на наличие оружия во второй руке.
    *   Проверяет навык `skill_dual_wield` (шанс срабатывания).
    *   Если прокнуло -> `mods["trigger_dual_wield"] = True`.

**Возвращает:** Два словаря `external_mods` (для Source и Target).

### B. Build Context (Public, Static)
Вызывается `Pipeline`'ом внутри задачи.

```python
def build_context(
    actor: ActorSnapshot, 
    target: ActorSnapshot | None, 
    move: CombatMoveDTO, 
    external_mods: dict = None
) -> PipelineContextDTO:
```

**Логика:**
1.  Создает пустой DTO.
2.  Применяет `external_mods`:
    *   `disable_attack` -> `phases.run_calculator = False`.
    *   `source_type="off_hand"` -> `flags.meta.source_type = "off_hand"`.
3.  Анализирует `move` (Skill/Item) и выставляет флаги (Magic, Ranged).

---

## 3. Структура PipelineContextDTO

```python
class PipelineContextDTO:
    # A. Управление Фазами
    phases: dict = {
        "run_pre_calc": True,
        "run_calculator": True, # False, если disable_attack
        "run_post_calc": True
    }

    # B. Флаги
    flags: dict = {
        "meta": {"source_type": "main_hand"}, # main_hand / off_hand
        "force": {"crit": False},
        "damage": {"physical": True}
    }

    # C. Модификаторы
    mods: dict = {}
```
