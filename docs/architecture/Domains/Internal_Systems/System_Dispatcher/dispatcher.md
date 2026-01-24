# ⚙️ Dispatcher Logic

[⬅️ Назад: Dispatcher Index](README.md)

## Метод `route()`

Единая точка входа для слабосвязанных вызовов.

```python
async def route(
    self,
    domain: str,          # Куда звоним (CoreDomain.COMBAT)
    action: str,          # Что хотим ("handle_action")
    context: dict = None, # Данные (payload)
) -> Any
```

⚠️ **Внимание:** Аргумент `session: AsyncSession` удален. Диспетчер работает в режиме Redis-only или вызывает сервисы, которые сами создают свои сессии (Self-Contained).

### Логика работы
1.  **Lookup:** Ищет зарегистрированную фабрику/инстанс для `domain`.
2.  **Execute:** Вызывает метод `get_entry_point(action, context)`.
3.  **Return:** Возвращает результат "как есть".

### Регистрация (Initialization)
В `internal.py` происходит сборка. Зависимости (включая `ContextAssembler`) внедряются **ДО** регистрации в диспетчере.

```python
# Пример сборки
# 1. Создаем зависимости (включая те, что работают с БД)
assembler = ContextAssemblerService() # Самостоятельный сервис
lifecycle = CombatLifecycleService(...)

# 2. Собираем Оркестратор (Прямая инъекция)
combat_orch = CombatEntryOrchestrator(
    lifecycle=lifecycle,
    assembler=assembler # <--- Передаем напрямую! Не через Dispatcher.
)

# 3. Регистрируем в Диспетчере
dispatcher.register(CoreDomain.COMBAT_ENTRY, lambda: combat_orch)
```