# Redis Storage Format

## Overview
Context Assembler сохраняет в Redis ТОЛЬКО отформатированные проекции.
Сырые данные (`core_*`) не сохраняются.

## Key Pattern
`temp:setup:{uuid4}`

## TTL
3600 seconds (1 hour)

## Storage Content by Scope

### `scope=combats`
Redis содержит DTO с ключами:
- `math_model` — v:raw structure (attributes, modifiers)
- `loadout` — belt, abilities, equipment_layout
- `vitals` — hp_current, energy_current
- `meta` — entity_id, type, character, symbiote

### `scope=inventory`
Redis содержит DTO с ключами:
- `inventory_structured` — items by categories
- `wallet_structured` — currency, resources, components
- `meta` — entity metadata

### `scope=status`
Redis содержит DTO с ключами:
- `stats_display` — formatted character stats
- `vitals_display` — HP/Energy with percentages
- `meta` — entity metadata

## Storage Process
1. Load raw data from DB → `core_*` fields
2. Create `TempContext(core_stats=..., core_inventory=...)`
3. Pydantic calls `@computed_field` methods
4. `model_dump(by_alias=True, exclude={"core_*"})`
5. Save ONLY projections to Redis
6. `core_*` discarded

## Important
- Consumers receive ONLY formatted projections
- No `core_*` fields in Redis
- Structure defined in `@computed_field` methods
