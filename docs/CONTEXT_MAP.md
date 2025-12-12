# 🗺️ CONTEXT MAP: ФАЙЛЫ ДЛЯ ЗАДАЧ

Этот документ помогает выбрать **минимально необходимый набор файлов** для загрузки в контекст нейросети при работе над конкретной задачей.

---

## 🛠️ Задача: Крафт (Обратная Инженерия)
**Суть:** Реализация механики разбора предметов (`Dismantle`), получения ресурсов и опыта профессии.
**Файлы для контекста:**
1.  `docs/dis_docs/02_Economy_and_Items/01_Economy_Craft_Loot.md` (ТЗ: Экономика и Крафт)
2.  `docs/dis_docs/04_Technical_Specs/04_Inventory_System.md` (ТЗ: Инвентарь)
3.  `apps/game_core/game_service/inventory/inventory_service.py` (Бизнес-логика инвентаря)
4.  `apps/common/database/repositories/ORM/inventory_repo.py` (Работа с БД предметов)
5.  `apps/common/schemas_dto/item_dto.py` (Структура предмета)
6.  `apps/common/database/model_orm/inventory.py` (Модели БД)

---

## 📜 Задача: Квесты (Генератор Контрактов)
**Суть:** Создание системы генерации заданий ("Убить N мобов", "Зачистить Разлом") и их выдачи через Доску Объявлений.
**Файлы для контекста:**
1.  `docs/dis_docs/01_Core_Mechanics/04_Quests_and_NPC_Systems.md` (ТЗ: Квесты)
2.  `apps/game_core/game_service/world/zone_orchestrator.py` (Пример генерации контента)
3.  `apps/game_core/game_service/world/content_gen_service.py` (Работа с LLM)
4.  `apps/common/resources/llm_data/mode_preset.py` (Промпты для ИИ)
5.  `apps/common/database/repositories/ORM/world_repo.py` (Доступ к миру)

---

## ⚔️ Задача: Боевая Система (PvP / Group)
**Суть:** Реализация матчмейкинга 1v1 и логики групповых боев (2v2+).
**Файлы для контекста:**
1.  `docs/dis_docs/01_Core_Mechanics/03_Combat_System.md` (ТЗ: Бой)
2.  `apps/game_core/game_service/combat/combat_turn_manager.py` (Движок асинхронных ходов)
3.  `apps/game_core/game_service/matchmaking_service.py` (Очереди поиска)
4.  `apps/game_core/game_service/combat/combat_service.py` (Фасад боя)
5.  `apps/bot/handlers/callback/game/combat/action_handlers.py` (Обработка действий игрока)

---

## 💰 Задача: Торговля (Аукцион)
**Суть:** Реализация биржи для обмена предметами между игроками за Пыль Резидуу.
**Файлы для контекста:**
1.  `docs/dis_docs/02_Economy_and_Items/01_Economy_Craft_Loot.md` (ТЗ: Экономика)
2.  `apps/common/database/repositories/ORM/inventory_repo.py` (Передача предметов)
3.  `apps/common/database/repositories/ORM/wallet_repo.py` (Работа с валютой)
4.  `apps/game_core/game_service/inventory/inventory_service.py` (Логика инвентаря)

---

## 🔮 Задача: Прокачка Дара и Симбиота
**Суть:** Реализация механики "кормления" Симбиота ресурсами и поглощения эссенции.
**Файлы для контекста:**
1.  `docs/dis_docs/01_Core_Mechanics/05_Symbiote_and_Gifts.md` (ТЗ: Симбиот)
2.  `apps/game_core/game_service/skill/skill_service.py` (Логика скиллов)
3.  `apps/common/database/model_orm/symbiote.py` (Модель Симбиота - если есть, или создать)
4.  `apps/common/schemas_dto/skill.py` (DTO навыков)

---

## 🛠️ Задача: Админка и Debug Tools
**Суть:** Реализация команд `/give_item`, `/teleport`, `/regen_zone`.
**Файлы для контекста:**
1.  `docs/dis_docs/04_Technical_Specs/05_Admin_and_Debug_Tools.md` (ТЗ: Админка)
2.  `apps/bot/handlers/admin/` (Папка для новых хэндлеров)
3.  `apps/common/database/repositories/ORM/inventory_repo.py` (Выдача предметов)
4.  `apps/game_core/game_service/world/zone_orchestrator.py` (Регенерация зон)
