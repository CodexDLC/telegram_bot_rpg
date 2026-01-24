# ⚙️ Context Assembler Service

## Описание
`ContextAssemblerService` — это **Stateless** сервис, который отвечает за координацию процесса сборки контекста.

Он не хранит состояние между запросами и не требует внешней сессии базы данных. Он создает короткоживущую сессию (`AsyncSession`) только на время выполнения метода `assemble`.

## API

### `assemble(request: ContextRequestDTO) -> ContextResponseDTO`

Основной метод.

1.  **Input:** DTO с ID сущностей и требуемым Scope.
2.  **Process:**
    *   Открывает транзакцию БД (Read-Only).
    *   Инициализирует стратегии (`PlayerAssembler`, `MonsterAssembler`).
    *   Запускает их параллельно (`asyncio.gather`).
    *   Агрегирует результаты.
3.  **Output:** DTO с маппингом ID -> Redis Key.

## Зависимости
*   `AccountManager` (Redis)
*   `ContextRedisManager` (Redis)
*   `async_session_factory` (SQLAlchemy Factory)

## Пример реализации

```python
async def assemble(self, request: ContextRequestDTO) -> ContextResponseDTO:
    async with async_session_factory() as session:
        # ... logic ...
```
