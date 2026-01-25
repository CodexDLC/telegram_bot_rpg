# 🏗️ Architecture V2 Vision: Hexagonal + Layered

> ℹ️ **SCOPE:** Данная структура описывает организацию **документации** (`docs/`).
> Кодовая база (`backend/`, `game_client/`) может отличаться — это нормально.

---

## 🤖 AI CONTEXT (Обязательно прочти первым)

> ⚠️ **ВАЖНО:** Эти документы описывают **структуру документации** (`docs/`), а НЕ структуру кода.
> Реальный код в `backend/`, `game_client/` организован иначе.

### ✅ Обязательная структура ЛЮБОГО домена (docs):
| Файл/Папка | Назначение |
|------------|-----------|
| `README.md` | Индекс — навигация внутри домена |
| `Manifest.md` | Паспорт — границы, зависимости, ответственность |
| `Roadmap/` | Задачи и план развития |
| `Changelog.md` | История изменений |
| `Specs/Testing/` | Стратегия тестирования домена |

### ⚙️ Опциональная структура (зависит от сложности):
Папки `API/`, `Orchestrator/`, `Engine/`, `Data/`, `Client_Interface/` — создаются **только если домен достаточно сложный** и требует детальной документации по слоям.

- **Простой домен** (Account, Status) → только обязательные файлы.
- **Сложный домен** (Combat, Inventory) → обязательные + слои архитектуры.

### 🚫 AI: НЕ ДЕЛАЙ ЭТО:
- Не требуй создания всех папок (API, Engine...) для каждого домена
- Не путай структуру документации со структурой кода
- Не предлагай "дополнить" домен папками, если пользователь не просит

### ✅ AI: ДЕЛАЙ ЭТО:
- Проверяй наличие обязательных файлов (Manifest, Roadmap, Changelog)
- Читай Manifest первым — там границы домена
- Читай Roadmap — там текущие задачи

---

Это эталон архитектуры Hexagonal + Layered (Гексагональная + Слоистая), адаптированная под задачи проекта.

## Структура Папок

```plaintext
docs/
├── 📂 management/                 # УПРАВЛЕНИЕ ПРОЕКТОМ (Задачи, Планы, Идеи)
│   ├── 📂 Standards/              # ❗ Гайдлайны по коду и неймингу
│   ├── 📂 idea/                   # Бэклог идей
│   ├── 📂 task/                   # Текущие задачи
│   ├── 📂 tech_debt/              # Технический долг
│   └── 📄 Project_Roadmap.md      # Глобальный план
│
├── 📂 designer/                   # ГЕЙМДИЗАЙН (Видение, Лор, Баланс)
│   ├── 📂 combat/                 # Видение боевки
│   ├── 📂 economy/                # Экономика
│   ├── 📂 rpg/                    # Ролевая система
│   └── 📂 world/                  # Лор и мир
│
└── 📂 architecture/               # ТЕХНИЧЕСКАЯ РЕАЛИЗАЦИЯ (Код, Схемы, API)
    ├── 📂 Domains/                # БИЗНЕС-ЛОГИКА (Features)
    │   │
    │   ├── 📂 User_Features/          # [Client-Facing] Домены, имеющие UI для игрока
    │   │   ├── 📂 Combat/             # Пример полного пользовательского домена
    │   │   │   ├── 📄 Manifest.md     # Паспорт домена
    │   │   │   ├── 📄 Roadmap.md      # План работ
    │   │   │   │
    │   │   │   ├── 📂 Client_Interface/   # СЛОЙ ПРЕДСТАВЛЕНИЯ
    │   │   │   │   └── 📂 Telegram/       # Специфика текущего клиента (handlers, keyboards, text)
    │   │   │   │
    │   │   │   ├── 📂 API/                # СЛОЙ GATEWAY (Вход в систему)
    │   │   │   │   └── 📄 Entry_Points.md # Методы, которые вызывает роутер/клиент
    │   │   │   │
    │   │   │   ├── 📂 Orchestrator/       # СЛОЙ СЕССИИ (Управление процессом)
    │   │   │   │   └── 📄 Flow_Manager.md # Логика связывания (SessionService)
    │   │   │   │
    │   │   │   ├── 📂 Engine/             # СЛОЙ МЕХАНИКИ (Чистые вычисления)
    │   │   │   │   └── 📄 Calculators.md  # Математика без БД
    │   │   │   │
    │   │   │   └── 📂 Data/               # СЛОЙ ДАННЫХ
    │   │   │       └── 📄 Storage.md      # Схемы Redis/DB
    │   │   │
    │   │   └── 📂 Inventory/          # Структура идентична Combat (см. выше)
    │   │       ├── 📂 Client_Interface/
    │   │       ├── 📂 API/
    │   │       ├── 📂 Orchestrator/
    │   │       ├── 📂 Engine/
    │   │       └── 📂 Data/
    │   │
    │   └── 📂 Internal_Systems/       # [System-Facing] Внутренние сервисы (без UI)
    │       └── 📂 Item_System/        # Пример внутреннего провайдера
    │           ├── 📄 Manifest.md
    │           ├── 📂 API/            # Internal Gateway (методы для других доменов)
    │           ├── 📂 Orchestrator/   # Factory logic, Transaction manager
    │           ├── 📂 Engine/         # RNG, Template parsers
    │           └── 📂 Data/           # DB Models, JSON Templates
    │
    ├── 📂 Core/                       # ОБЩИЕ ДВИЖКИ (Shared Engines)
    │   ├── 📂 RPG_Rules/              # "Физика мира" (Stateless)
    │   │   ├── 📂 Attributes/
    │   │   ├── 📂 Skills/
    │   │   └── 📂 Formulas/
    │   │
    │   └── 📂 Context_System/         # Сборщик данных (Query Engine)
    │       ├── 📂 Aggregators/        # Сборка данных игрока/монстра
    │       └── 📂 Query_Planner/      # Оптимизатор запросов
    │
    ├── 📂 Infrastructure/             # ТЕХНИЧЕСКИЙ ФУНДАМЕНТ (Drivers)
    │   ├── 📂 Database/               # Postgres (Repositories, Models)
    │   ├── 📂 Redis/                  # Cache, Queue Managers
    │   └── 📂 External/               # API сторонних сервисов (AI, Analytics)
    │
    └── 📂 Drafts/                     # ПЕСОЧНИЦА
        ├── 📂 Incoming_Ideas/
        └── 📂 Diagrams/
```

## Правила размещения файлов

1.  **Client_Interface/Telegram:** Если это касается отображения в Telegram (кнопки, текст, HTML).
2.  **API:** Если это входная точка (Gateway), принимающая запрос.
3.  **Orchestrator:** Если это управление состоянием или процессом (SessionService).
4.  **Engine:** Если это чистая математика или алгоритм (без базы данных). Или Core/RPG_Rules если это общее.
5.  **Data:** Если это схема БД, DTO или Redis.
6.  **Internal_Systems:** Если сервис не имеет UI и обслуживает другие системы.

## ⛔ Naming Convention (Правила именования)

1.  **NO NUMBERING:** Запрещено использовать префиксы `01_`, `02_` в именах файлов документации.
    *   ❌ `01_Pipeline.md`
    *   ✅ `Pipeline.md`
2.  **Snake_Case or Pascal_Case:** Используйте подчеркивания для читаемости.
    *   ✅ `Combat_Resolver.md`
3.  **Descriptive Names:** Имя файла должно четко отражать компонент или концепцию.