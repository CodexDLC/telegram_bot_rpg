# Player Assembler

## Component
`PlayerAssembler`

## Responsibility
Loads raw player data from database, formats it using TempContext schemas, saves projections to Redis.

## Key Method
```python
async def process_batch(player_ids: list[int], scope: str) -> dict[int, str]
```

## Logic Flow
1. Get Query Plan from scope (which tables to load)
2. Load raw data from DB in parallel:
   - `db.get_attributes(player_ids)`
   - `db.get_inventory(player_ids)`
   - `db.get_skills(player_ids)`
   - `db.get_vitals(player_ids)` [Redis]
   - etc.
3. Select TempContext class based on scope:
   - `scope=combats` → `CombatTempContext`
   - `scope=inventory` → `InventoryTempContext`
   - `scope=status` → `StatusTempContext`
4. For each player:
   - Create TempContext instance with `core_*` data
   - Pydantic calls `@computed_field` methods
   - `model_dump(by_alias=True, exclude={"core_*"})`
   - Save ONLY projections to Redis with TTL
5. Return `{player_id: redis_key}` mapping

## Design Pattern
**Strategy Pattern** - different TempContext classes for different scopes.

## Performance
Uses `asyncio.gather()` for parallel DB queries. Typical time: ~80ms for 10 players.
