# 🏗️ Repositories Registry

⬅️ [Назад](./README.md)

> **Source:** `apps/common/database/repositories/ORM/`

Мы используем паттерн **Repository** для абстракции доступа к данным.
Реализации репозиториев находятся в папке `ORM`.

## 🏭 Factory Pattern (Dependency Injection)

В файле `__init__.py` реализован паттерн **Factory Functions**.
Мы не создаем экземпляры репозиториев напрямую (`UsersRepoORM(...)`), а используем фабричные функции.

### Пример
```python
# apps/common/database/repositories/__init__.py

def get_user_repo(session: AsyncSession) -> IUserRepo:
    """
    Единственная точка связывания Интерфейса и Реализации.
    Если мы захотим сменить ORM на сырой SQL, мы поменяем код только здесь.
    """
    return UsersRepoORM(session=session)
```

**Зачем это нужно:**
1.  **Decoupling:** Бизнес-логика зависит от абстракции (`IUserRepo`), а не от конкретного класса (`UsersRepoORM`).
2.  **Testing:** В тестах можно легко подменить реализацию на Mock, просто переопределив фабрику.

---

## 📂 Registry

### 👤 User & Character
*   **UsersRepoORM** (`users_repo_orm.py`) — Работа с пользователями.
*   **CharactersRepoORM** (`characters_repo_orm.py`) — Работа с персонажами.
*   **SymbioteRepoORM** (`symbiote_repo.py`) — Данные симбиота.
*   **WalletRepoORM** (`wallet_repo.py`) — Операции с валютой.

### 🎒 Inventory & Skills
*   **InventoryRepo** (`inventory_repo.py`) — Управление инвентарем.
*   **SkillProgressRepo** (`skill_repo.py`) — Прогресс навыков.

### 🌍 World & Content
*   **WorldRepoORM** (`world_repo.py`) — Локации и перемещение.
*   **MonsterRepository** (`monster_repository.py`) — Данные монстров.
*   **ScenarioRepository** (`scenario_repository.py`) — Сценарии и квесты.

### 🏆 Meta
*   **LeaderboardRepoORM** (`leaderboard_repo.py`) — Рейтинги.
