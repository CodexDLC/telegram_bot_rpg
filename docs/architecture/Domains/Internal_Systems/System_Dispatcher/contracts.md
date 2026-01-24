# 📜 Contracts & Protocols

[⬅️ Назад: Dispatcher Index](README.md)

## Протокол Оркестратора

```python
async def get_entry_point(self, action: str, context: dict[str, Any]) -> Any:
    """
    Точка входа. Должна быть Stateless (не зависеть от внешней сессии БД).
    """
```

## 🚫 Анти-паттерны (Чего делать нельзя)

### 1. Передача Session через Context
**Плохо:**
```python
# Caller
await dispatcher.route(..., context={"session": db_session}) # ❌ ЗАПРЕЩЕНО
```
**Хорошо:** Оркестратор сам открывает `async with async_session_maker()` внутри метода, если ему нужно сходить в Postgres. Или использует инжектированный сервис (Saver/Assembler).

### 2. Вызов Data-сервисов через Dispatcher
**Плохо:**
```python
# Пытаемся получить данные для инициализации через роут
data = await dispatcher.route(CoreDomain.CONTEXT_ASSEMBLER, ...) # ❌ ЗАПРЕЩЕНО
```
**Хорошо:** Используйте Direct Dependency Injection в конструкторе вашего класса:

```python
class MyOrchestrator:
    def __init__(self, assembler: ContextAssemblerService):
        self.assembler = assembler # ✅ Прямой вызов
```

### Пример правильной реализации (Combat Entry)
```python
class CombatEntryOrchestrator:
    def __init__(self, assembler: ContextAssemblerService, ...):
        self.assembler = assembler

    async def get_entry_point(self, action: str, context: dict) -> Any:
        if action == "start_pve":
            # 1. Сами загружаем данные (Assembler сам управляет БД)
            data = await self.assembler.assemble(context["char_id"])
            
            # 2. Работаем с Redis
            return await self._start_session(data)
```