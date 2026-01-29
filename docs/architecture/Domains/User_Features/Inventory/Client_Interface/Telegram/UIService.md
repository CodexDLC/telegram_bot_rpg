# 🎨 Inventory UI Service & Formatters

[⬅️ Назад: Telegram Client](./README.md)

---

## 🎯 Описание
Этот слой отвечает за **презентацию**.
Использует **строго типизированные DTO** для доступа к данным, исключая использование "магических строк" и словарей.

---

## 🏗️ Архитектура UI-слоя

### 1. `InventoryUIService` (Фасад)
**Файл:** `features/inventory/system/inventory_ui_service.py`

```python
class InventoryUIService(BaseUIService):
    def render(self, payload: InventoryUIPayloadDTO) -> ViewResultDTO:
        if payload.screen == "main":
            return self.doll_ui.render(payload)
        elif payload.screen == "bag":
            return self.bag_ui.render(payload)
        # ...
```

### 2. UI Компоненты (Пример: `BagUI`)
**Файл:** `features/inventory/components/bag_ui.py`

```python
class BagUI:
    def render(self, payload: InventoryUIPayloadDTO) -> ViewResultDTO:
        # 1. Type Guard (Гарантируем тип контекста)
        if not isinstance(payload.context, BagContextDTO):
            raise ValueError(f"Invalid context for BagUI: {type(payload.context)}")
            
        context = payload.context  # Теперь IDE знает, что это BagContextDTO

        # 2. Форматирование текста
        text = InventoryFormatter.format_bag(context)

        # 3. Сборка клавиатуры
        builder = InlineKeyboardBuilder()
        
        # 3.1. Сетка предметов (доступ через точку!)
        item_grid = self._build_item_grid(context.items)
        builder.row(*item_grid)
        
        # 3.2. Пагинация (доступ через точку!)
        pagination_row = self._build_pagination_row(context.pagination)
        builder.row(*pagination_row)
        
        return ViewResultDTO(text=text, kb=builder.as_markup())

    def _build_pagination_row(self, pagination: PaginationDTO) -> list:
        # IDE подскажет: pagination.has_next, pagination.page
        if pagination.has_next:
            # ...
        pass
```

### 3. Форматтеры
**Файл:** `features/inventory/resources/formatters/inventory_formatter.py`

```python
class InventoryFormatter:
    @staticmethod
    def format_bag(context: BagContextDTO) -> str:
        lines = []
        for item in context.items:
            lines.append(f"- {item.data.name}")
        return "\n".join(lines)
```
