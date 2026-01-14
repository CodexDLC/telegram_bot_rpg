# 💾 Schema: Triggers (Триггеры)

[⬅️ Назад: Data Schemas](./README.md) | [📖 Правила: Items](../Items/README.md)

---

## 📋 Обзор
Техническая реализация триггеров — правил, связывающих события боя с эффектами.

## ⚙️ DTO Structure

```python
from pydantic import BaseModel

class TriggerData(BaseModel):
    id: str                 # "trigger_bleed"
    name_ru: str            # "Кровотечение"
    event: str              # "ON_CRIT", "ON_HIT"
    chance: float = 1.0     # 1.0 = 100%
    effect: str             # "apply_bleed" (ключ для AbilityService)
    metadata: dict          # Параметры эффекта {"damage": 5}
```

## 📝 Пример: On Crit Bleed
```python
trigger_bleed = {
    "id": "trigger_bleed",
    "name_ru": "Кровотечение",
    "event": "ON_CRIT",
    "chance": 1.0,
    "effect": "apply_bleed",
    "metadata": {"damage_percent": 0.2}
}
```
