class RedisKeys:
    """
    Предоставляет статические методы для генерации стандартизированных ключей Redis.

    Этот класс гарантирует, что все компоненты приложения используют
    единый формат для ключей Redis, что упрощает управление данными
    и предотвращает конфликты.
    """

    @staticmethod
    def get_account_key(char_id: int) -> str:
        """
        Генерирует ключ для хранения динамических данных аккаунта персонажа в Redis (тип HASH).

        Хранит такие данные, как текущее состояние FSM, ID локации,
        предыдущее состояние и локацию.

        Args:
            char_id: Уникальный идентификатор персонажа.

        Returns:
            Строка-ключ в формате "ac:{char_id}". Пример: "ac:1001".
        """
        return f"ac:{char_id}"

    @staticmethod
    def get_world_location_meta_key(loc_id: str) -> str:
        """
        Генерирует ключ для хранения статичных метаданных мировой локации (тип HASH).

        Содержит информацию о названии, описании, доступных выходах и т.д.

        Args:
            loc_id: Уникальный идентификатор локации.

        Returns:
            Строка-ключ в формате "world:loc:{loc_id}". Пример: "world:loc:portal_plats".
        """
        return f"world:loc:{loc_id}"

    @staticmethod
    def get_world_location_players_key(loc_id: str) -> str:
        """
        Генерирует ключ для хранения идентификаторов игроков, находящихся в данной локации (тип SET).

        Args:
            loc_id: Уникальный идентификатор локации.

        Returns:
            Строка-ключ в формате "world:players_loc:{loc_id}". Пример: "world:players_loc:portal_plats".
        """
        return f"world:players_loc:{loc_id}"

    @staticmethod
    def get_solo_dungeon_key(char_id: int) -> str:
        """
        Генерирует ключ для хранения состояния одиночного подземелья (тип HASH).

        Идентификатор подземелья совпадает с ID персонажа. Хранит такие данные,
        как текущая комната, здоровье босса, найденные ключи и т.д.

        Args:
            char_id: Уникальный идентификатор персонажа.

        Returns:
            Строка-ключ в формате "s_d:{char_id}". Пример: "s_d:1001".
        """
        return f"s_d:{char_id}"

    @staticmethod
    def get_group_dungeon_key(instance_id: str) -> str:
        """
        Генерирует ключ для хранения состояния группового подземелья (тип HASH).

        `instance_id` — это уникальный идентификатор, генерируемый при входе группы.

        Args:
            instance_id: Уникальный идентификатор инстанса группового подземелья.

        Returns:
            Строка-ключ в формате "g_d:{instance_id}". Пример: "g_d:grp_a4b1_elf_cave".
        """
        return f"g_d:{instance_id}"

    @staticmethod
    def get_combat_actor_key(session_id: str, char_id: int) -> str:
        """
        Генерирует ключ для хранения данных конкретного участника боевой сессии.

        Args:
            session_id: Уникальный идентификатор боевой сессии.
            char_id: Уникальный идентификатор персонажа-участника.

        Returns:
            Строка-ключ в формате "combat:sess:{session_id}:actor:{char_id}".
        """
        return f"combat:sess:{session_id}:actor:{char_id}"

    @staticmethod
    def get_combat_pending_move_key(session_id: str, actor_id: int, target_id: int) -> str:
        """
        Генерирует ключ для хранения информации о незавершенном ходе одного актора против другого в боевой сессии.

        Args:
            session_id: Уникальный идентификатор боевой сессии.
            actor_id: Идентификатор актора, совершающего ход.
            target_id: Идентификатор цели хода.

        Returns:
            Строка-ключ в формате "combat:sess:{session_id}:pending:{actor_id}:{target_id}".
            Пример: "combat:sess:123:pending:1001:2002".
        """
        return f"combat:sess:{session_id}:pending:{actor_id}:{target_id}"

    @staticmethod
    def get_combat_pending_move_pattern(session_id: str, actor_id: int) -> str:
        """
        Генерирует паттерн для поиска всех незавершенных ходов, инициированных данным актором в боевой сессии.

        Args:
            session_id: Уникальный идентификатор боевой сессии.
            actor_id: Идентификатор актора, чьи ходы ищутся.

        Returns:
            Строка-паттерн в формате "combat:sess:{session_id}:pending:{actor_id}:*".
        """
        return f"combat:sess:{session_id}:pending:{actor_id}:*"

    @staticmethod
    def get_combat_log_key(session_id: str) -> str:
        """
        Генерирует ключ для хранения логов боевой сессии (тип LIST, используется RPUSH).

        Args:
            session_id: Уникальный идентификатор боевой сессии.

        Returns:
            Строка-ключ в формате "combat:sess:{session_id}:logs".
        """
        return f"combat:sess:{session_id}:logs"

    @staticmethod
    def get_combat_meta_key(session_id: str) -> str:
        """
        Генерирует ключ для хранения метаданных боевой сессии (тип HASH).

        Содержит общую информацию, такую как время начала, тип боя (PvE/PvP) и статус активности.

        Args:
            session_id: Уникальный идентификатор боевой сессии.

        Returns:
            Строка-ключ в формате "combat:sess:{session_id}:meta".
        """
        return f"combat:sess:{session_id}:meta"

    @staticmethod
    def get_combat_participants_key(session_id: str) -> str:
        """
        Генерирует ключ для хранения идентификаторов всех участников боевой сессии (тип SET).

        Args:
            session_id: Уникальный идентификатор боевой сессии.

        Returns:
            Строка-ключ в формате "combat:sess:{session_id}:participants".
        """
        return f"combat:sess:{session_id}:participants"

    @staticmethod
    def get_arena_queue_key(mode: str) -> str:
        """
        Генерирует ключ для очереди арены (тип ZSET).

        Args:
            mode: Режим арены (например, "1v1", "group").

        Returns:
            Строка-ключ в формате "arena:queue:{mode}:zset". Пример: "arena:queue:1v1:zset".
        """
        return f"arena:queue:{mode}:zset"

    @staticmethod
    def get_arena_request_key(char_id: int) -> str:
        """
        Генерирует ключ для хранения метаданных заявки персонажа на арену (тип HASH/STRING).

        Содержит информацию, такую как время подачи заявки и текущий GameState.

        Args:
            char_id: Уникальный идентификатор персонажа.

        Returns:
            Строка-ключ в формате "arena:req:{char_id}". Пример: "arena:req:1001".
        """
        return f"arena:req:{char_id}"

    @staticmethod
    def get_player_status_key(char_id: int) -> str:
        """
        Генерирует ключ для хранения текущего статуса игрока для межсервисного взаимодействия.

        Пример значения: 'combat:session_id' или 'arena:queue'.

        Args:
            char_id: Уникальный идентификатор персонажа.

        Returns:
            Строка-ключ в формате "player:status:{char_id}". Пример: "player:status:1001".
        """
        return f"player:status:{char_id}"
