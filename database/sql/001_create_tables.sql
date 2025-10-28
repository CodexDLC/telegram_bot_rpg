CREATE TABLE IF NOT EXISTS users(
    telegram_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT,
    username TEXT,
    language_code TEXT DEFAULT 'ru',
    is_premium  INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'now')),
    updated_at TEXT DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'now'))
);

CREATE TABLE IF NOT EXISTS characters(
    character_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT DEFAULT 'Новый персонаж',
    gender TEXT DEFAULT 'other',
    created_at  TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'now')),

    FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS character_stats(
    character_id INTEGER PRIMARY KEY,
    strength INTEGER DEFAULT 4,
    dexterity INTEGER DEFAULT 4,
    endurance INTEGER DEFAULT 4,
    charisma INTEGER DEFAULT 4,
    intelligence INTEGER DEFAULT 4,
    perception INTEGER DEFAULT 4,
    luck INTEGER DEFAULT 4,
    created_at  TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'now')),

    FOREIGN KEY (character_id) REFERENCES characters (character_id) ON DELETE CASCADE
);


