# 🗄️ ORM Models Registry

⬅️ [Назад](./README.md)

> **Source:** `apps/common/database/model_orm/`

Полный список таблиц базы данных (SQLAlchemy Models).

## 👤 Users & Characters
*   **User** (`user.py`) — Telegram-пользователь.
*   **Character** (`character.py`) — Игровой персонаж.
*   **Symbiote** (`symbiote.py`) — Данные симбиота и даров.
*   **Wallet** (*Inferred*) — Кошелек (валюты).

## 🎒 Inventory & Progression
*   **InventorySlot** (`inventory.py`) — Предметы в инвентаре.
*   **SkillProgress** (`skill.py`) — Прокачка навыков персонажа.

## 🌍 World & Content
*   **Location** / **Region** (`world.py`) — Локации и регионы.
*   **Monster** (`monster.py`) — Справочник монстров.
*   **ScenarioState** (`scenario.py`) — Состояние квестов и сценариев.

## 🏆 Meta
*   **LeaderboardEntry** (`leaderboard.py`) — Таблицы рекордов.
