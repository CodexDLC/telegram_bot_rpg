# Combat Exchange Architecture (RBC v2.0)

Этот документ описывает архитектуру `CombatExchangeOrchestrator` — центрального узла, управляющего любым взаимодействием в бою (Удар, Хил, Бафф, AoE).

## 1. Концепция: Map-Reduce Pipeline

Процесс обработки действия разбит на 4 стадии. Стадии 1-3 выполняются **параллельно** для каждой цели (Map). Стадия 4 собирает результаты и применяет их атомарно (Reduce/Commit).

### Ключевые принципы
1.  **Stateless Logic:** Сервисы внутри пайплайна (Ability, Calculator, Mechanics) не пишут в БД. Они возвращают "Дельты" (изменения).
2.  **Strategy Pattern:** Оркестратор выбирает стратегию в зависимости от типа действия (Standard, Instant, AoE).
3.  **Deferred Commit:** Все изменения применяются только в конце, что позволяет избежать гонок данных при массовых ударах.

---

## 2. Поток Данных (The Flow)

```mermaid
sequenceDiagram
    participant Orch as ExchangeOrchestrator
    participant Strat as ExchangeStrategy
    participant Abil as AbilityService (State)
    participant Calc as CombatCalculator (Math)
    participant Mech as MechanicsService (Resources)
    participant Agg as ResultAggregator
    participant DB as Redis

    Note over Orch: 1. Initialization
    Orch->>Strat: Select Strategy (Standard / Instant)
    Strat-->>Orch: Target List & Flags

    Note over Orch: 2. Parallel Execution (Map)
    par For Each Target
        Orch->>Abil: Pre-Calc (Inject Flags/Temp Stats)
        
        opt If Strategy needs Hit Calc
            Orch->>Calc: Calculate Hit (Atk vs Def)
        end
        
        Orch->>Abil: Post-Calc (Triggers & Status Lifecycle)
        Note right of Abil: "Crit -> Apply Poison", "Extend Buff"
        
        Orch->>Mech: Calculate Resources (Formulas)
        Note right of Mech: HP: "-10 (Hit) +5 (Vamp)", EN: "-15"
    end

    Note over Orch: 3. Aggregation (Reduce)
    Orch->>Agg: Collect all Deltas & Logs
    Agg->>Agg: Sum HP/EN changes, Build Log String

    Note over Orch: 4. Commit
    Orch->>DB: Pipeline Write (State & Logs)
```