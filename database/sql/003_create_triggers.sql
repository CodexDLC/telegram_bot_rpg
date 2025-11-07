-- 003_create_triggers.sql
-- Этот скрипт создает триггеры для автоматизации некоторых
-- действий в базе данных, таких как обновление временных меток
-- и создание связанных записей.

-- =================================================================
-- Триггер: trg_users_update_timestamp
-- Таблица: users
-- Событие: AFTER UPDATE
-- Описание: Автоматически обновляет поле `updated_at` при любом
--           изменении записи в таблице `users`.
-- Условие: Срабатывает, только если `updated_at` не было обновлено
--          в самом UPDATE-запросе, чтобы избежать рекурсии.
-- =================================================================
CREATE TRIGGER IF NOT EXISTS trg_users_update_timestamp
AFTER UPDATE ON users
FOR EACH ROW
WHEN OLD.updated_at = NEW.updated_at -- Предотвращение рекурсивного вызова
BEGIN
    UPDATE users
    SET updated_at = (STRFTIME('%Y-%m-%d %H:%M:%f', 'now'))
    WHERE telegram_id = OLD.telegram_id;
END;

-- =================================================================
-- Триггер: trg_characters_update_timestamp
-- Таблица: characters
-- Событие: AFTER UPDATE
-- Описание: Автоматически обновляет `updated_at` при изменении
--           записи в таблице `characters`.
-- =================================================================
CREATE TRIGGER IF NOT EXISTS trg_characters_update_timestamp
AFTER UPDATE ON characters
FOR EACH ROW
WHEN OLD.updated_at = NEW.updated_at
BEGIN
    UPDATE characters
    SET updated_at = (STRFTIME('%Y-%m-%d %H:%M:%f', 'now'))
    WHERE character_id = OLD.character_id;
END;

-- =================================================================
-- Триггер: trg_character_stats_update_timestamp
-- Таблица: character_stats
-- Событие: AFTER UPDATE
-- Описание: Автоматически обновляет `updated_at` при изменении
--           записи в таблице `character_stats`.
-- =================================================================
CREATE TRIGGER IF NOT EXISTS trg_character_stats_update_timestamp
AFTER UPDATE ON character_stats
FOR EACH ROW
WHEN OLD.updated_at = NEW.updated_at
BEGIN
    UPDATE character_stats
    SET updated_at = (STRFTIME('%Y-%m-%d %H:%M:%f', 'now'))
    WHERE character_id = OLD.character_id;
END;

-- =================================================================
-- Триггер: trg_auto_create_stats
-- Таблица: characters
-- Событие: AFTER INSERT
-- Описание: Автоматически создает запись с базовыми характеристиками
--           в таблице `character_stats` сразу после создания
--           нового персонажа в таблице `characters`.
--           Это обеспечивает консистентность данных.
-- =================================================================
CREATE TRIGGER IF NOT EXISTS trg_auto_create_stats
AFTER INSERT ON characters
FOR EACH ROW
-- Проверка, чтобы избежать ошибок, если статы уже были созданы
WHEN NOT EXISTS (SELECT 1 FROM character_stats WHERE character_id = NEW.character_id)
BEGIN
    INSERT INTO character_stats (character_id)
    VALUES (NEW.character_id);
END;
