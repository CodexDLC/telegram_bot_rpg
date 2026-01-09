# Combat System Documentation Index

## 🎯 Start Here
1. [00_COMBAT_CONCEPT.md](00_COMBAT_CONCEPT.md) - Philosophy
2. [01_RBC_MANIFESTO.md](01_RBC_MANIFESTO.md) - Core Rules
3. [04_refactoring_roadmap_v3.md](04_refactoring_roadmap_v3.md) - Current Status

## 📊 Data Structures
- [02_combat_dtos_spec.md](02_combat_dtos_spec.md) - Python DTOs
- [03_combat_data_structure.md](03_combat_data_structure.md) - Redis Schema
- [05_actor_data_structure.md](05_actor_data_structure.md) - Actor Layout

## ⚙️ Services (by execution order)
1. **Infrastructure** (Red Layer)
   - [infrastructure/01_combat_initialization.md](infrastructure/01_combat_initialization.md)
   - [infrastructure/02_combat_router_spec.md](infrastructure/02_combat_router_spec.md)

2. **Logic** (Blue Layer)
   - [logic/01_universal_stats_engine_spec.md](logic/01_universal_stats_engine_spec.md)
   - [logic/02_combat_calculator_spec.md](logic/02_combat_calculator_spec.md)
   - [logic/03_ability_service_spec.md](logic/03_ability_service_spec.md)
   - [logic/07_trigger_system_spec.md](logic/07_trigger_system_spec.md)

3. **Workers** (Green Layer)
   - [workers/01_worker_manager_spec.md](workers/01_worker_manager_spec.md)
   - [workers/02_worker_executor_spec.md](workers/02_worker_executor_spec.md)

## 🔮 Features (v3.1 WIP)
- [features/02_feints_library_spec.md](features/02_feints_library_spec.md)
- [features/03_trigger_system_spec.md](features/03_trigger_system_spec.md)
- [features/04_intent_system_spec.md](../../features/04_intent_system_spec.md)
- [features/05_zone_resolution_spec.md](../../features/05_zone_resolution_spec.md)
- [features/06_token_economy_spec.md](../../features/06_token_economy_spec.md)
- [features/07_gifts_skills_interaction.md](../../features/07_gifts_skills_interaction.md)
