# 🧩 Components

⬅️ [Назад](../README.md)

Полный список компонентов системы RBC v3.0.

## ⚙️ Core Engine
*   [**CombatResolver**](./combat_resolver.md) — Математическое ядро (расчет урона).
*   [**Pipeline**](./pipeline.md) — Цепочка обработки удара.
*   [**ContextBuilder**](./context_builder.md) — Сборка контекста перед расчетом.
*   [**StatsEngine**](./stats_engine.md) — Калькулятор характеристик.
*   [**TargetResolver**](./target_resolver.md) — Выбор целей (Self, Enemy, All).

## 🔄 Processors & Workers
*   [**TurnManager**](./turn_manager.md) — Прием заявок и валидация.
*   [**Collector (Processor)**](./collector_processor.md) — Логика матчмейкинга.
*   [**Collector (Task)**](./collector_task.md) — ARQ задача коллектора.
*   [**Executor (Logic)**](./executor.md) — Логика исполнения действий.
*   [**Executor (Task)**](./executor_worker.md) — ARQ задача исполнителя.
*   [**AI Worker**](./ai_worker.md) — Бот (Ghost Agent).
*   [**Chaos Task**](./chaos_task.md) — Фоновая очистка (Garbage Collector).

## 🛠️ Services
*   [**AbilityService**](./ability_service.md) — Эффекты и абилки.
*   [**MechanicsService**](./mechanics_service.md) — Применение урона и мутация стейта.
*   [**LifecycleService**](./initialization.md) — Создание и инициализация боя.
*   [**ChaosService**](./chaos_service.md) — Логика призыва Time Eater.
*   [**ViewService**](./view_service.md) — Подготовка данных для UI.
*   [**Finalizer**](./finalizer.md) — Завершение боя и выдача наград.

## 🔌 API & Data
*   [**Ingress API (Gateway)**](./ingress_api.md) — Точка входа для клиентов.
*   [**Data Layer**](./data_layer/combat_data_service.md) — Работа с Redis.

## ✨ Features
*   [**Trigger System**](./features/trigger_system.md) — Система флагов и триггеров.
*   [**Feints Library**](./features/feints_library.md) — Библиотека финтов.
