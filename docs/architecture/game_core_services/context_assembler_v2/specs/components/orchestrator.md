# Context Assembler Orchestrator

## Component
`ContextAssemblerOrchestrator`

## Responsibility
Single entry point for Context Assembler. Coordinates parallel execution of Player, Monster, and Pet assemblers.

## Key Method
```python
async def assemble(request: ContextRequestDTO) -> ContextResponseDTO
```

## Logic Flow
1. Receives `ContextRequestDTO` (player_ids, monster_ids, pet_ids, scope)
2. Distributes tasks to specialized assemblers in parallel:
   - `PlayerAssembler.process_batch(player_ids, scope)`
   - `MonsterAssembler.process_batch(monster_ids, scope)`
   - `PetAssembler.process_batch(pet_ids, scope)` [future]
3. Uses `asyncio.gather()` for concurrent execution
4. Collects results from all assemblers
5. Handles errors (failed IDs go to `response.errors`)
6. Returns `ContextResponseDTO` with Redis key mappings

## Design Pattern
**Facade Pattern** - provides simple interface, delegates complex work to specialized assemblers.

## Error Handling
- Assembler failures don't break entire request
- Failed entity IDs collected in `response.errors`
- Successful entities still returned
