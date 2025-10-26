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



