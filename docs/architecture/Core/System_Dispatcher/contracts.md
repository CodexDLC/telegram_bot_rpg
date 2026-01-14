# 📜 Contracts & Protocols

[⬅️ Назад: Dispatcher Index](./README.md)

## Протокол Оркестратора

Чтобы домен мог быть вызван через `SystemDispatcher`, его главный класс (Orchestrator) должен реализовывать следующий метод:

```python
async def get_entry_point(self, action: str, context: dict[str, Any]) -> Any:
    """
    Единая точка входа для внутренних запросов.
    
    Args:
        action: Имя действия (например, "get_item_info", "check_status").
        context: Словарь с аргументами (char_id, item_id и т.д.).
        
    Returns:
        Любой объект (обычно Pydantic DTO или примитив).
    """
```

## Пример реализации (Inventory)

```python
class InventoryCoreOrchestrator:
    async def get_entry_point(self, action: str, context: dict) -> Any:
        if action == "get_capacity":
            return await self.get_capacity(context["char_id"])
            
        elif action == "add_item":
            return await self.add_item(context["char_id"], context["item_id"])
            
        raise ValueError(f"Unknown action: {action}")
```

## Пример вызова (из другого домена)

```python
# Combat хочет узнать вместимость инвентаря
capacity = await dispatcher.route(
    domain=CoreDomain.INVENTORY,
    action="get_capacity",
    context={"char_id": 123}
)
```

---

## 🔥 Real-World Case: Scenario запускает PvE Бой

Сценарий (Scenario Service) хочет инициировать битву с монстром. Он не импортирует Combat напрямую, а использует Диспетчер.

### 1. Вызов (Scenario Service)
```python
# Внутри ScenarioLogic
response = await self.dispatcher.route(
    domain=CoreDomain.COMBAT_ENTRY,
    action="create_pve_session",
    context={
        "char_id": player_id,
        "enemy_id": "rat_king_boss"
    }
)

if response.status == "error":
    # Обработка ошибки (например, игрок уже в бою)
    return self.show_error(response.message)

# Успех -> Сценарий завершается, управление переходит к Бою
```

### 2. Обработка (Combat Entry Orchestrator)
```python
class CombatEntryOrchestrator:
    async def get_entry_point(self, action: str, context: dict) -> CoreResponseDTO:
        if action == "create_pve_session":
            try:
                # Создаем сессию и переключаем стейт игрока внутри сервиса
                await self.service.create_session(
                    char_id=context["char_id"],
                    enemies=[context["enemy_id"]]
                )
                return CoreResponseDTO(status="success")

            except PlayerBusyError:
                return CoreResponseDTO(
                    status="error",
                    message="Player is already in combat"
                )
```