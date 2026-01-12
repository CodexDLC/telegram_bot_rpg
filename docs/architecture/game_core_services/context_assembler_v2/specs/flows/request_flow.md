# Request Flow

## End-to-End Flow

### Step 1: Consumer Initiates Request
```python
# Combat System / Status Service / Inventory Service
response = await context_assembler.assemble(
    ContextRequestDTO(
        player_ids=[101, 102],
        monster_ids=["uuid-1", "uuid-2"],
        scope="combats"
    )
)
```

### Step 2: Orchestrator Distributes Tasks
```python
# ContextAssemblerOrchestrator.assemble()
player_results, monster_results = await asyncio.gather(
    player_assembler.process_batch(request.player_ids, request.scope),
    monster_assembler.process_batch(request.monster_ids, request.scope)
)
```

### Step 3: PlayerAssembler Executes
```python
# PlayerAssembler.process_batch()
query_plan = QUERY_PLANS[scope]  # ["attributes", "inventory", "skills", ...]

# Parallel DB queries
attributes, inventory, skills, vitals = await asyncio.gather(
    db.get_attributes(player_ids),
    db.get_inventory(player_ids),
    db.get_skills(player_ids),
    redis.get_vitals(player_ids)
)

# Format for each player
for player_id in player_ids:
    context = CombatTempContext(
        core_stats=attributes[player_id],
        core_inventory=inventory[player_id],
        # ...
    )
    temp_data = context.model_dump(by_alias=True, exclude={"core_*"})
    redis_key = f"temp:setup:{uuid4()}"
    await redis.json().set(redis_key, "$", temp_data, ex=3600)
    results[player_id] = redis_key
```

### Step 4: Orchestrator Returns Response
```python
return ContextResponseDTO(
    player={101: "temp:setup:uuid-a", 102: "temp:setup:uuid-b"},
    monster={"uuid-1": "temp:setup:uuid-c", "uuid-2": "temp:setup:uuid-d"}
)
```

### Step 5: Consumer Uses Data
```python
# Combat System reads formatted projections
temp_data = await redis.json().get(response.player[101])
math_model = temp_data["math_model"]  # Ready to use!
await redis.json().set(f"combat:rbc:{sid}:actor:{id}:raw", "$", math_model)
```

## Performance
Общее время: ~80ms для 10 игроков (параллельное выполнение на 3 уровнях: Orchestrator, Assembler, Redis pipeline).
