# 🗺️ CONTEXT MAP: ФАЙЛЫ ДЛЯ ЗАДАЧ

Этот документ помогает выбрать **минимально необходимый набор файлов** для загрузки в контекст нейросети при работе над конкретной задачей.

---

## ⚔️ Задача: Рефакторинг финализации боя (Refactor_Combat_Finalization)
**Суть:** Разделить логику завершения боя (награды, последствия) в зависимости от режима игры (PvE, PvP, Tutorial) с помощью `CombatMode` enum.

**Файлы для контекста:**
1.  `docs/tusk/Refactor_Combat_Finalization.md` (Основной таск)
2.  `apps/common/schemas_dto/combat_source_dto.py` (Для добавления `CombatMode` enum)
3.  `apps/game_core/game_service/combat/combat_lifecycle_service.py` (Основной сервис, где будет `match/case` логика)
4.  `apps/common/services/core_service/manager/combat_manager.py` (Для получения метаданных сессии)
5.  `apps/game_core/game_service/arena/arena_manager.py` (Место вызова `create_battle` с `CombatMode.ARENA`)
6.  `apps/game_core/game_service/exploration/encounter_service.py` (Место вызова `create_battle` с `CombatMode.ADVENTURE`)
7.  `apps/game_core/game_service/tutorial/tutorial_service.py` (Место вызова `create_battle` с `CombatMode.TUTORIAL`)

---

## 🎓 Задача: Рефакторинг системы обучения (Refactor_Tutorial_System)
**Суть:** Заменить старый, хардкодный туториал на полноценный игровой сценарий, использующий реальные игровые сервисы и `CombatMode.TUTORIAL`.

**Файлы для контекста:**
1.  `docs/tusk/Refactor_Tutorial_System.md` (Основной таск)
2.  `apps/game_core/game_service/tutorial/tutorial_service.py` (Новый сервис-оркестратор)
3.  `apps/bot/handlers/callback/tutorial/` (Папка со старыми хэндлерами, которые нужно переписать)
4.  `apps/game_core/game_service/inventory/inventory_service.py` (Для выдачи стартового лута)
5.  `apps/game_core/game_service/skill/skill_service.py` (Для разблокировки стартового навыка)
6.  `apps/game_core/game_service/combat/combat_lifecycle_service.py` (Для инициации и завершения тренировочного боя)
7.  `apps/game_core/resources/game_data/tutorial/` (Папка для конфигов мобов и предметов туториала)

---

## 🎲 Задача: Реализация системы Риска и Награды (Task_Risk_Reward_Implementation)
**Суть:** Внедрение механики "незащищенного" лута и опыта, которые можно потерять при смерти в опасных зонах (Рифтах).

**Файлы для контекста:**
1.  `docs/tusk/Task_Risk_Reward_Implementation.md` (Основной таск)
2.  `apps/common/database/model_orm/inventory.py` (Добавление флага `is_secured` в модель `InventoryItem`)
3.  `apps/common/database/model_orm/character.py` (Добавление `secured_xp` в модель `CharacterStats`)
4.  `apps/game_core/game_service/inventory/inventory_service.py` (Изменение `add_item` и добавление `secure_all_items`)
5.  `apps/bot/ui_service/navigation_service.py` (Добавление триггеров сохранения в безопасных зонах)
6.  `apps/game_core/game_service/combat/combat_xp_manager.py` (Разделение логики `add_xp` и `checkpoint_xp`)
7.  `apps/game_core/game_service/combat/combat_lifecycle_service.py` (Логика потери лута в `_finalize_adventure`)
8.  `apps/common/services/core_service/manager/world_manager.py` (Для реализации системы "трупов" в Redis)
9.  `apps/bot/ui_service/helpers_ui/formatters/inventory_formatter.py` (Для визуального отображения `is_secured`)

---

## 🌲 Задача: Группа навыков Survival (Refined)
**Суть:** Реализация навыков выживания, влияющих на взаимодействие с миром, а не прямую боевую мощь.

**Список навыков:**
1.  **Adaptation (Адаптация):**
    * *Effect:* Снижает входящий урон от эффектов окружения (Environmental Hazards) в Рифтах.
    * *Gain:* Начисление XP за каждый тик полученного (и пережитого) урона от среды.

2.  **Pathfinder (Следопыт):**
    * *Effect:* Модификатор формулы инициативы. Повышает шанс получить статус `DETECTED` при энкаунтере.
    * *Gain:* Начисление XP за каждое успешное обнаружение врага или открытие новой зоны.

3.  **Taming (Укрощение):**
    * *Trigger:* Доступно ТОЛЬКО в состоянии `DETECTED` против типа `BEAST`/`DRAGON`.
    * *Interaction:* Запускает альтернативный сценарий "Taming Combat", где цель — не убить, а заполнить прогресс-бар (через кормление, удержание урона или скилл-чеки).
    * *Gain:* Большой прирост XP при успешном приручении.

**Файлы для контекста:**
1.  `apps/game_core/game_service/skill/skill_service.py` (Регистрация новой ветки)
2.  `apps/game_core/game_service/exploration/encounter_engine.py` (Логика Initiative Check для Pathfinder)
3.  `apps/game_core/game_service/world/threat_service.py` (Расчет урона среды для Adaptation)
4.  `apps/bot/ui_service/helpers_ui/formatters/navigation_formatter.py` (Добавление кнопки "Приручить" в меню энкаунтера при условии Detected + Beast)

---

## ⚙️ Backend: Энкаунтеры (Two-Step Check)
**Суть:** Реализация двухступенчатой системы: 1. Спавн (ГСЧ + Тир), 2. Инициатива (Навыки vs Навыки).
**Файлы для контекста:**
1.  `apps/game_core/game_service/world/threat_service.py` (Данные о Тире зоны)
2.  `apps/game_core/resources/game_data/monsters/spawn_config.py` (Конфиги спавна мобов)
3.  `apps/game_core/game_service/modifiers_calculator_service.py` (Получение статов Stealth/Perception игрока)
4.  *New File:* `apps/game_core/game_service/exploration/encounter_engine.py` (Вся математика тут: try_spawn и calculate_initiative)

---

## ☣️ Задача: Энкаунтеры (Rift Leak Mechanic)
**Суть:** Механика "Протечки". Если рядом есть Рифт, его монстры могут встретиться в обычном мире.
**Файлы для контекста:**
1.  `apps/game_core/game_service/exploration/encounter_engine.py` (Основная логика шансов)
2.  `apps/common/services/core_service/manager/world_manager.py` (Добавить метод `get_nearby_rifts(x, y)`)
3.  `apps/game_core/game_service/rift/rift_manager.py` (Получение данных о монстрах внутри активного рифта)

---

## 🌀 Задача: Рифты (Template System & Reuse)
**Суть:** Реализация системы "Шаблон" (общая карта) + "Инстанс" (личный прогресс). Генерация шаблона при старте квеста, переиспользование для других игроков.
**Файлы для контекста:**
1.  `apps/common/database/model_orm/world.py` (Модели: `RiftTemplate`, `RiftInstance`, **`RiftHistory`**)
2.  `apps/game_core/game_service/rift/rift_generator.py` (Создает Template: топологию и заказывает тексты у LLM сразу)
3.  `apps/game_core/game_service/rift/rift_manager.py` (Логика: SQL запрос на поиск "непосещенных" -> иначе вызов Generator)
4.  `apps/game_core/game_service/rift/rift_service.py` (Логика прохождения: проверка state_data в Instance vs structure в Template)
5.  `apps/game_core/game_service/exploration/encounter_engine.py` (Генерация стычек при переходе между нодами)
6.  `apps/common/services/gemini_service/gemini_service.py` (Генерация описаний для Narrative Content)

---

## 🧬 Задача: Монстры и Кланы (Scalable Families)
> ⚠️ **Requires Review:** Требует пересмотра с оглядкой на текущую структуру проекта (`ClanFactory`, `MonsterStructs`).
**Суть:** Реализация кланов с диапазоном тиров (Tier Range). Один клан может населять разные рифты, меняя состав миньонов.
**Файлы для контекста:**
1.  `apps/game_core/resources/game_data/monsters/monster_structs.py` (Добавить в структуру `Clan` поля `min_tier`, `max_tier`)
2.  `apps/game_core/game_service/monster/clan_factory.py` (Логика выбора состава пака в зависимости от Тира Рифта)
3.  `apps/game_core/resources/game_data/monsters/spawn_config.py` (Конфигурация спавна)

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
