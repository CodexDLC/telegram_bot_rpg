# Worker Flows (Asynchronous Layer)

⬅️ [Назад](../README.md) | 🏠 [Документация](../../../../README.md)

В этом документе описаны асинхронные процессы, происходящие в фоне (ARQ Workers).

---

## 1. Collector Flow (Matchmaking)
**Цель:** Сбор заявок, поиск пар и запуск исполнителей.
**Trigger:** Сигнал от `TurnManager` или Таймер.

```mermaid
graph TD
    Trigger[Signal / Timer] --> A(CollectorTask)
    A -->|Load Meta & Moves| B[CombatCollector]
    B -->|Check AI| C{AI Missing?}
    C -->|Yes| D[Dispatch AI Task]
    B -->|Harvest Instant| E[Actions Queue]
    B -->|Match Exchange| E
    B -->|Check Timeout| F{Timeout?}
    F -->|Yes| G[Create Force Action]
    G --> E
    E -->|Batch > 0| H[Dispatch Executor]

    click A "../components/collector_task.md" "CollectorTask Spec"
    click B "../components/collector_processor.md" "CollectorProcessor Spec"
    click D "../components/ai_worker.md" "AI Worker Spec"
```

---

## 2. Executor Flow (Processing Loop)
**Цель:** Расчет физики боя и применение изменений.
**Trigger:** Задача от `Collector`.

```mermaid
graph TD
    A(ExecutorTask) -->|Load Full Context| B[(Redis)]
    A -->|Try Acquire Lock| C{Lock Acquired?}
    C -->|No| Stop[Stop: Busy]
    C -->|Yes| D[CombatExecutor]
    
    subgraph Loop [Action Processing Loop]
        D -->|Next Action| E{Type?}
        E -->|Exchange| F[Generate Tasks]
        E -->|Instant| G[Generate Tasks]
        
        subgraph Pipeline [Combat Pipeline]
            H[ContextBuilder] --> I[AbilityService: Pre-Calc]
            I --> J[StatsEngine: Recalculate]
            J --> K{Liveness Check}
            K -->|Dead| Skip
            K -->|Alive| L[CombatResolver]
            L --> M[AbilityService: Post-Calc]
            M --> N[MechanicsService: Commit]
        end
        
        F --> Pipeline
        G --> Pipeline
    end

    Pipeline -->|Result| O[Aggregate Logs]
    O -->|Loop End| D
    D -->|All Done| P[Commit Session]
    P -->|Save Batch| Q[(Redis)]
    Q -->|Signal| R[Heartbeat -> Collector]

    click A "../components/executor_worker.md" "ExecutorTask Spec"
    click D "../components/executor.md" "Executor Logic Spec"
    click H "../components/context_builder.md" "ContextBuilder Spec"
    click I "../components/ability_service.md" "AbilityService Spec"
    click J "../components/stats_engine.md" "StatsEngine Spec"
    click L "../components/combat_resolver.md" "CombatResolver Spec"
    click N "../components/mechanics_service.md" "MechanicsService Spec"
```

---

## 3. AI Flow (Bot Logic)
**Цель:** Принятие решения за NPC.
**Trigger:** Задача от `Collector`.

```mermaid
graph TD
    A(AiTurnTask) -->|Load Context| B[GhostAgent]
    B -->|Analyze Tokens| C[Decision Logic]
    C -->|Select Action| D[Intent]
    D -->|Register Batch| E[TurnManager]
    E -->|Push| F[(Redis: Moves)]

    click A "../components/ai_worker.md" "AI Worker Spec"
    click E "../components/turn_manager.md" "TurnManager Spec"
```
