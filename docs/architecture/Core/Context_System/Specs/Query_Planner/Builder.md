# 🗺️ Query Plan Builder

[⬅️ Назад: Specs](../README.md)

---

## 🎯 Описание
Строит план загрузки данных на основе `scope`.

## ⚙️ Логика

```python
class QueryPlanBuilder:
    def build(self, scope: str) -> QueryPlan:
        plan = QueryPlan()
        
        # Base (всегда)
        plan.add_load("character_base")
        
        if scope == "combats":
            plan.add_load("attributes")
            plan.add_load("skills")
            plan.add_load("inventory", filter="equipped")
            
        elif scope == "inventory":
            plan.add_load("inventory", filter="all")
            plan.add_load("wallet")
            
        return plan
```
