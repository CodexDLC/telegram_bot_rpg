# ⚙️ Combat Engine (Core Logic)

[⬅️ Назад: Combat Domain](../README.md)

---

## 🎯 Обзор
**Combat Engine** — это сердце боевой системы. Здесь происходит вся магия: от обработки заявки игрока до расчета урона и начисления опыта.
Движок построен на принципе **асинхронного пайплайна** (Async Pipeline).

## 📂 Структура

### 1. [Logic (Чистая Логика)](./Logic/README.md)
Компоненты, отвечающие за математику и правила.
*   **[Pipeline Core](./Logic/Pipeline_Core.md):** Алгоритм расчета одного удара.
*   **[Calculators](./Logic/Calculators.md):** Математическое ядро (Waterfall Stats, RNG).
*   **[Mechanics](./Logic/Mechanics_Service.md):** Мутация стейта (HP, XP).
*   **[Abilities](./Logic/Ability_Service.md):** Эффекты и скиллы.
*   **[Targeting](./Logic/Targeting.md):** Выбор целей.

### 2. [Processors (Оркестрация)](./Processors/README.md)
Компоненты, управляющие потоком выполнения.
*   **[Collector](./Processors/Collector.md):** Сборщик заявок и матчмейкинг пар.
*   **[Executor](./Processors/Executor.md):** Исполнитель боевых раундов.

---

## 🔄 Architecture Overview (Как это работает)

### 1. Exchange Pipeline (Размен ударами)
Классический ход в бою (Атака на Атаку). Требует синхронизации двух участников.

```mermaid
graph TD
    PlayerA[Player A] -->|Move| TM[Turn Manager]
    PlayerB[Player B] -->|Move| TM
    
    TM -->|Buffer| Redis[(Redis Queue)]
    
    subgraph Engine Processors
        Redis -->|Check Pairs| Collector[Collector Service]
        Collector -->|CombatAction\n(Exchange)| Executor[Executor Service]
    end
    
    subgraph Core Logic
        Executor -->|1. Context| CB[Context Builder]
        CB -->|2. Pipeline| CP[Combat Pipeline]
        CP -->|3. Result| Mech[Mechanics Service]
    end
    
    Mech -->|Commit| Redis
```

### 2. Instant Pipeline (Мгновенное действие)
Использование предмета или скилла без ответа (Buff, Heal). Не ждет второго игрока.

```mermaid
graph TD
    Player[Player] -->|Move (Instant)| TM[Turn Manager]
    TM -->|Buffer| Redis[(Redis Queue)]
    
    subgraph Engine Processors
        Redis -->|Check Immediate| Collector[Collector Service]
        Collector -->|CombatAction\n(Instant)| Executor[Executor Service]
    end
    
    subgraph Core Logic
        Executor -->|1. Context| CB[Context Builder]
        CB -->|2. Pipeline| CP[Combat Pipeline]
        CP -->|3. Result| Mech[Mechanics Service]
    end
    
    Mech -->|Commit| Redis
```
