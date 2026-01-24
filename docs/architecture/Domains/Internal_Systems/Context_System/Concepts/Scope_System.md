# 🔭 Scope System

[⬅️ Назад: Concepts](README.md)

---

## 🎯 Что такое Scope?
Scope (Область видимости) — это строковый идентификатор, который определяет:
1.  Какие данные нужны клиенту.
2.  Какие таблицы БД нужно прочитать.
3.  Какой DTO сформировать на выходе.

---

## 📋 Список Scopes

### 1. `combats`
**Цель:** Подготовка к бою (RBC).
**Загружает:**
*   Attributes (Сила, Ловкость...)
*   Vitals (HP, Energy)
*   Skills (Боевые)
*   Inventory (Только экипированное)
*   Symbiote (Дары)
**DTO:** `CombatTempContext`

### 2. `status`
**Цель:** Экран "Статус персонажа".
**Загружает:**
*   Attributes
*   Vitals
*   Symbiote
**DTO:** `StatusTempContext`

### 3. `inventory`
**Цель:** Экран "Инвентарь" или "Торговля".
**Загружает:**
*   Inventory (Весь: экипированное + сумка)
*   Wallet (Золото, Ресурсы)
**DTO:** `InventoryTempContext`

---

## ⚙️ Как это работает?

```python
# QueryPlanBuilder
if scope == "combats":
    plan.add_table("attributes")
    plan.add_table("skills")
    plan.add_table("inventory", filter="equipped")

elif scope == "inventory":
    plan.add_table("inventory", filter="all")
    plan.add_table("wallet")
```
