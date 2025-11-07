-- 001_create_tables.sql
-- Этот скрипт создает основные таблицы, необходимые для работы бота.

-- =================================================================
-- Таблица: users
-- Описание: Хранит информацию о пользователях Telegram, которые
--           запустили бота.
-- =================================================================
CREATE TABLE IF NOT EXISTS users (
    telegram_id   INTEGER PRIMARY KEY,      -- Уникальный ID пользователя в Telegram
    first_name    TEXT    NOT NULL,         -- Имя пользователя
    last_name     TEXT,                     -- Фамилия пользователя (опционально)
    username      TEXT,                     -- Никнейм пользователя (опционально)
    language_code TEXT    DEFAULT 'ru',     -- Языковой код (по умолчанию 'ru')
    is_premium    INTEGER DEFAULT 0,        -- Флаг Premium-подписки Telegram (0 - нет, 1 - да)
    created_at    TEXT    DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'now')), -- Время создания записи
    updated_at    TEXT    DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'now'))  -- Время последнего обновления
);

-- =================================================================
-- Таблица: characters
-- Описание: Хранит информацию об игровых персонажах, созданных
--           пользователями.
-- =================================================================
CREATE TABLE IF NOT EXISTS characters (
    character_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Уникальный ID персонажа в игре
    user_id      INTEGER NOT NULL,                   -- ID владельца персонажа (внешний ключ)
    name         TEXT    DEFAULT 'Новый персонаж',   -- Имя персонажа
    gender       TEXT    DEFAULT 'other',            -- Пол персонажа
    game_stage   TEXT    NOT NULL DEFAULT 'creation',-- Текущий этап игры для персонажа
    created_at   TEXT    NOT NULL DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'now')),
    updated_at   TEXT    NOT NULL DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'now')),

    -- Внешний ключ, связывающий персонажа с пользователем.
    -- ON DELETE CASCADE: при удалении пользователя, все его персонажи
    -- также будут автоматически удалены.
    FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
);

-- =================================================================
-- Таблица: character_stats
-- Описание: Хранит основные характеристики (S.P.E.C.I.A.L.)
--           для каждого персонажа.
-- =================================================================
CREATE TABLE IF NOT EXISTS character_stats (
    character_id INTEGER PRIMARY KEY, -- ID персонажа (одновременно и внешний ключ)
    strength     INTEGER DEFAULT 4,   -- Сила
    perception   INTEGER DEFAULT 4,   -- Восприятие
    endurance    INTEGER DEFAULT 4,   -- Выносливость
    charisma     INTEGER DEFAULT 4,   -- Харизма
    intelligence INTEGER DEFAULT 4,   -- Интеллект
    agility      INTEGER DEFAULT 4,   -- Ловкость
    luck         INTEGER DEFAULT 4,   -- Удача
    created_at   TEXT    NOT NULL DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'now')),
    updated_at   TEXT    NOT NULL DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'now')),

    -- Связь "один-к-одному" с таблицей персонажей.
    -- При удалении персонажа его характеристики также удаляются.
    FOREIGN KEY (character_id) REFERENCES characters (character_id) ON DELETE CASCADE
);
