# Effect Factory

**Class:** `EffectFactory`
**Path:** `apps.game_core.modules.combat.combat_engine.logic.effect_factory`
**Type:** Static Helper / Factory

## 🎯 Ответственность
Инкапсулирует логику создания и настройки `ActiveEffectDTO`.
Отвечает за расчет финальных параметров эффекта (Impact, Mutations) на основе конфигурации, входных параметров и контекста боя.
Обеспечивает унифицированный способ создания эффектов из разных источников (Абилки, Финты, Триггеры).

---

## ⚙️ Логика работы

Фабрика принимает на вход:
1.  **Config:** `EffectConfigDTO` (из GameData).
2.  **Params:** `EffectParams` (инструкции из Абилки/Триггера).
3.  **Context:** `damage_ref` (урон удара), `source_id`, `current_exchange`.

И возвращает:
1.  **DTO:** Готовый `ActiveEffectDTO`.
2.  **Mutations:** Словарь изменений статов (`raw_modifiers`), которые нужно применить к актору.

### Алгоритм расчета

1.  **Base Data:**
    *   `duration`: Берется из `params` (приоритет) или `config`.
    *   `power`: Берется из `params` (default 1.0).

2.  **Impact Calculation (Ресурсы - DOT/HOT):**
    *   **Special Logic (Bleed):** Если эффект имеет тег `bleed` и передан `damage_ref > 0`:
        *   `impact = damage_ref * 0.3 * power`. (30% от урона, скалируется павером).
        *   Игнорирует базовый импакт из конфига.
    *   **Standard Logic (Poison/Burn):**
        *   Берет `base_impact` из `config.resource_impact` (или `params.impact`, если передан).
        *   `impact = base_impact * power`.

3.  **Mutations Calculation (Статы - Buff/Debuff):**
    *   Собирает мутации из `config.raw_modifiers`.
    *   Добавляет мутации из `params.mutations` (динамические).
    *   *Примечание:* `power` пока не применяется к мутациям статов (но архитектура позволяет).

4.  **Control Logic (Флаги):**
    *   Берет `config.control_logic`.
    *   Если в `params` передан `control`, использует его (приоритет).

---

## 📦 Data Structures

### EffectParams (TypedDict)
Унифицированная структура параметров наложения эффекта.

```python
class EffectParams(TypedDict):
    duration: int          # Переопределяет длительность
    power: float           # Множитель силы (для Impact и Bleed)
    impact: dict[str, int] # Прямое задание ресурсов (редко)
    mutations: dict        # Динамические статы (для Buff)
    control: dict          # Динамические флаги (редко)
    remove_on: list[str]   # Условия снятия
```

---

## 🛠️ Integration

Используется исключительно в `AbilityService` (Post-Calc этап).

```python
# Пример вызова
active_effect, mutations = EffectFactory.create_effect(
    config=config,
    params=params,
    source_id=source.char_id,
    current_exchange=current_exchange,
    damage_ref=ctx.result.damage_final # Для скалирования от урона
)

# Применение
_apply_raw_mutations(target, mutations)
target.statuses.effects.append(active_effect)
```
