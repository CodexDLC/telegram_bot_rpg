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
