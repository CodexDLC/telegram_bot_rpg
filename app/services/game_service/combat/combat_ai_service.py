import random


class CombatAIService:
    """
    Логика поведения NPC (ИИ).
    """

    # --- 1. ЛОГИКА ОБЫЧНОГО МОБА (Линейная) ---
    @staticmethod
    def generate_mob_response(mob_id: int, player_attack_zones: list[str]) -> dict[str, list[str]]:
        """
        Моб делает ход в ответ на атаку игрока.
        Генерирует и защиту (от текущей атаки), и свою атаку.
        """
        # 1. Защита (Рандом, моб не знает, куда бьет игрок... или знает?)
        # Допустим, тупой моб просто закрывает 2 случайные зоны
        all_zones = ["head", "chest", "legs", "feet"]
        block = random.sample(all_zones, 2)

        # 2. Атака (Рандом)
        attack = [random.choice(all_zones)]

        return {"attack": attack, "block": block}

    # --- 2. ЛОГИКА БОССА (Параллельная) ---

    @staticmethod
    def generate_boss_reactive_block(boss_id: int) -> list[str]:
        """
        Поток А: Реактивная защита.
        Босс генерирует блок МГНОВЕННО в момент удара игрока.
        """
        # Босс умный, он может закрывать 3 зоны из 4
        all_zones = ["head", "chest", "legs", "feet"]
        return random.sample(all_zones, 3)

    @staticmethod
    def select_aggro_target(boss_data: dict, participants: dict) -> int:
        """
        Поток Б: Выбор цели для спец-удара (по таймеру).
        """
        # 1. Фильтруем живых игроков
        living_players = [
            p_id
            for p_id, p_data in participants.items()
            if p_data["team"] == "blue" and p_data["state"]["hp_current"] > 0
        ]

        if not living_players:
            return 0

        # TODO: Сюда прикрутим таблицу Aggro (кто больше надамажил)
        # Пока рандом
        return int(random.choice(living_players))
