# app/services/core_service/redis_key.py


class RedisKeys:
    """
    Класс-пространство имен для генерации ключей Redis.

    Использует @staticmethod, чтобы выступать в роли "библиотеки"
    для всех Менеджеров. Гарантирует, что все части
    приложения используют единый формат ключей.
    """

    @staticmethod
    def get_account_key(char_id: int) -> str:
        """
        Ключ для ХЭША (Hash) с динамическими данными персонажа.

        Хранит: state, location_id, prev_state, prev_location_id и т.д.
        Пример: "ac:1001"
        """
        return f"ac:{char_id}"

    # --- 1. Мировые локации (World) ---

    @staticmethod
    def get_world_location_meta_key(loc_id: str) -> str:
        """
        Ключ для ХЭША (Hash) со статичными мета-данными мировой локации.

        Хранит: name, description, exits (json) и т.д.
        Пример: "world:loc:portal_plats"
        """
        # Используем твой префикс world:loc:
        return f"world:loc:{loc_id}"

    @staticmethod
    def get_world_location_players_key(loc_id: str) -> str:
        """
        Ключ для МНОЖЕСТВА (Set) с ID игроков в мировой локации.

        Пример: "world:players:portal_plats"
        """
        # (Тут я предлагаю 'world:players:' для ясности,
        # чтобы не путать с 'world:loc:')
        return f"world:players_loc:{loc_id}"

    # --- 2. Одиночные Подземелья (Solo Dungeon) ---

    @staticmethod
    def get_solo_dungeon_key(char_id: int) -> str:
        """
        Ключ для ХЭША (Hash) с состоянием ОДИНОЧНОГО подземелья.

        ID инстанса данжа = ID персонажа.
        Хранит: current_room_id, boss_hp, key_found и т.д.
        Пример: "s_d:1001"
        """
        # Используем твой префикс s_d:
        return f"s_d:{char_id}"

    # --- 3. Групповые Подземелья (Group Dungeon) ---

    @staticmethod
    def get_group_dungeon_key(instance_id: str) -> str:
        """
        Ключ для ХЭША (Hash) с состоянием ГРУППОВОГО подземелья.

        instance_id - это уникальный ID, сгенерированный
        при входе группы в данж.
        Пример: "g_d:grp_a4b1_elf_cave"
        """
        # Используем твой префикс g_d:
        return f"g_d:{instance_id}"

    @staticmethod
    def get_combat_actor_key(session_id: str, char_id: int) -> str:
        return f"combat:sess:{session_id}:actor:{char_id}"

    @staticmethod
    def get_combat_pending_move_key(session_id: str, actor_id: int, target_id: int) -> str:
        """
        🔥 ИЗМЕНЕНО: Теперь ключ зависит от ПАРЫ (Кто -> Кого).
        Пример: combat:sess:123:pending:1001:2002
        """
        return f"combat:sess:{session_id}:pending:{actor_id}:{target_id}"

    @staticmethod
    def get_combat_pending_move_pattern(session_id: str, actor_id: int) -> str:
        """
        Паттерн для поиска ВСЕХ заявок этого игрока (ко всем врагам).
        """
        return f"combat:sess:{session_id}:pending:{actor_id}:*"

    @staticmethod
    def get_combat_log_key(session_id: str) -> str:
        """Redis List для логов боя (rpush)."""
        return f"combat:sess:{session_id}:logs"

    @staticmethod
    def get_combat_meta_key(session_id: str) -> str:
        """Общая инфа: {start_time, type (pve/pvp), is_active}."""
        return f"combat:sess:{session_id}:meta"

    @staticmethod
    def get_combat_participants_key(session_id: str) -> str:
        """Ключ для Set с ID всех участников боя."""
        return f"combat:sess:{session_id}:participants"

    @staticmethod
    def get_arena_queue_key(mode: str) -> str:
        """
        Ключ для ZSET очереди.
        Пример: "arena:queue:1v1:zset"
        """
        return f"arena:queue:{mode}:zset"

    @staticmethod
    def get_arena_request_key(char_id: int) -> str:
        """
        Ключ для ХЭША/Строки с мета-данными заявки (время старта, GS).
        Пример: "arena:req:1001"
        """
        return f"arena:req:{char_id}"

    @staticmethod
    def get_player_status_key(char_id: int) -> str:
        """
        Статус игрока для межсервисного взаимодействия.
        Пример: 'combat:session_id' или 'arena:queue'.
        Ключ: "player:status:1001"
        """
        return f"player:status:{char_id}"
