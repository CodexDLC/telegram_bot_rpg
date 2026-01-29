# 📦 Inventory DTOs

[⬅️ Назад: Inventory Data](./Resources.md)

---

## 🎯 Описание
Описание контрактов данных. Используется **строгая типизация** (Pydantic Models).

---

## 📡 API Response Strategy

Инвентарь использует **Global Composite Response** для реализации двухпанельного UI.

**Response Type:** `CoreCompositeResponseDTO` (из `common.schemas.response`)
*   `header`: `GameStateHeader`
*   `payload`: `InventoryUIPayloadDTO` (Контент Инвентаря)
*   `menu_payload`: `MenuDTO` (Контент HUD)

---

## 📦 Content Payload DTOs

### `InventoryUIPayloadDTO`
Данные для отрисовки основного экрана (Content).

```python
# Union всех возможных контекстов
InventoryContext = BagContextDTO | DollContextDTO | DetailsContextDTO

class InventoryUIPayloadDTO(BaseModel):
    screen: str  # 'main', 'bag', 'details'
    title: str
    description: str
    
    # Строго типизированный контекст!
    context: InventoryContext
    
    buttons: list[ButtonDTO]
```

### `ButtonDTO`
Универсальное описание кнопки.

```python
class ButtonDTO(BaseModel):
    text: str
    action: str
    payload: dict[str, Any] | None = None
    is_active: bool = True
    style: str = "primary"
```

---

## 🧩 Context DTOs (Screen Specific)

Эти DTO описывают структуру данных для конкретных экранов (`context`).

### `PaginationDTO`
```python
class PaginationDTO(BaseModel):
    page: int
    total_pages: int
    has_next: bool
    has_prev: bool
```

### `BagContextDTO` (Для Сумки/Сетки)
```python
class BagContextDTO(BaseModel):
    items: list[InventoryItemDTO]
    pagination: PaginationDTO
    active_filter: str
    back_target: str | None = None
```

### `DollContextDTO` (Для Куклы)
```python
class DollContextDTO(BaseModel):
    equipped: dict[str, InventoryItemDTO]
    stats: dict[str, Any]
    wallet: WalletDTO
```

### `DetailsContextDTO` (Для Карточки/Сравнения)
```python
class DetailsContextDTO(BaseModel):
    item: InventoryItemDTO
    comparison_item: InventoryItemDTO | None = None
    back_target: str
```

---

## 💾 Internal DTOs (Redis)
*   `InventorySessionDTO`
*   `InventoryItemDTO`

---

## 📱 Client DTOs
*   `UnifiedViewDTO`
*   `ViewResultDTO`
