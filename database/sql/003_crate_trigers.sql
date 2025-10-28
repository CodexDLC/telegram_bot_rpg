

CREATE TRIGGER IF NOT EXISTS trg_users_update_timestamp
AFTER UPDATE ON users
FOR EACH ROW
WHEN OLD.updated_at = NEW.updated_at
BEGIN
    UPDATE users
    SET updated_at = (STRFTIME('%Y-%m-%d %H:%M:%f', 'now'))
    WHERE telegram_id = OLD.telegram_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_characters_update_timestamp
AFTER UPDATE ON characters
FOR EACH ROW
WHEN OLD.updated_at = NEW.updated_at
BEGIN
    UPDATE characters
    SET updated_at = (STRFTIME('%Y-%m-%d %H:%M:%f', 'now'))
    WHERE character_id = OLD.character_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_character_stats_update_timestamp
AFTER UPDATE ON character_stats
FOR EACH ROW
WHEN OLD.updated_at = NEW.updated_at
BEGIN
    UPDATE character_stats
    SET updated_at = (STRFTIME('%Y-%m-%d %H:%M:%f', 'now'))
    WHERE
    character_id = OLD.character_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_auto_create_stats
AFTER INSERT ON characters
FOR EACH ROW
WHEN NOT EXISTS (SELECT 1 FROM character_stats WHERE character_id = NEW.character_id)
BEGIN
    INSERT INTO character_stats (character_id)
    VALUES (NEW.character_id);
END;