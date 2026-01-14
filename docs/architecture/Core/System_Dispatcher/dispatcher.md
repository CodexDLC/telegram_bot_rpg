# ⚙️ Dispatcher Logic

[⬅️ Назад: Dispatcher Index](./README.md)

## Метод `route()`

Единая точка входа для внутренних вызовов.

```python
async def route(
    self,
    domain: str,          # Куда звоним (CoreDomain.INVENTORY)
    action: str,          # Что хотим ("add_item")
    context: dict = None, # Данные
    session: AsyncSession = None # Опционально
) -> Any
```

### Логика обработки сессии
1.  **Check:** Проверяет, входит ли `domain` в список `_DB_DOMAINS` (требующих БД).
2.  **Reuse:** Если `session` передана — использует её.
3.  **Create:** Если сессии нет, но она нужна — создает временную (`async with get_async_session()`).
4.  **Skip:** Если сессия не нужна (Redis-only домен) — передает `None`.

## Фабрика Оркестраторов
Диспетчер использует `CoreContainer` для получения экземпляра нужного сервиса и инъекции в него сессии.

```python
# Пример
if domain == CoreDomain.INVENTORY:
    return self.container.get_inventory_core_orchestrator(session)
```

## Требования к Доменам
Каждый оркестратор, вызываемый через Диспетчер, должен реализовывать метод:
```python
async def get_entry_point(self, action: str, context: dict) -> Any:
    ...
```