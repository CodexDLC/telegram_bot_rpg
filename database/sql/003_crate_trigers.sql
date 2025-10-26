

CREATE TRIGGER IF NOT EXISTS trg_users_update_timestamp
AFTER UPDATE ON users
FOR EACH ROW
WHEN OLD.updated_at = NEW.updated_at
BEGIN
    UPDATE users
    SET updated_at = (STRFTIME('%Y-%m-%d %H:%M:%f', 'now'))
    WHERE telegram_id = OLD.telegram_id;
END;

