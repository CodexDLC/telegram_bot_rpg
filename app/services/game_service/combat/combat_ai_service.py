# app/services/game_service/combat/combat_ai_service.py
import random

from loguru import logger as log


class CombatAIService:
    """
    Сервис для генерации действий NPC (ИИ) в бою.

    Содержит логику для различных типов поведения: от простых мобов
    до сложных боссов с несколькими потоками принятия решений.
    """

    # --- 1. ЛОГИКА ОБЫЧНОГО МОБА (Линейная) ---
    @staticmethod
    def generate_mob_response(mob_id: int, player_attack_zones: list[str]) -> dict[str, list[str]]:
        """
        Генерирует ответный ход для простого моба.

        Моб делает ход в ответ на атаку игрока, генерируя одновременно
        и свою защиту, и свою атаку.

        Args:
            mob_id (int): ID моба.
            player_attack_zones (list[str]): Зоны, которые атакует игрок (пока не используется).

        Returns:
            dict[str, list[str]]: Словарь с ключами 'attack' и 'block'.
        """
        log.debug(f"Генерация хода для моба ID: {mob_id}.")

        # 1. Защита: Тупой моб просто закрывает 2 случайные зоны.
        all_zones = ["head", "chest", "legs", "feet"]
        block = random.sample(all_zones, 2)
        log.debug(f"Моб {mob_id} выбрал для блока: {block}.")

        # 2. Атака: Моб атакует одну случайную зону.
        attack = [random.choice(all_zones)]
        log.debug(f"Моб {mob_id} выбрал для атаки: {attack}.")

        return {"attack": attack, "block": block}

    # --- 2. ЛОГИКА БОССА (Параллельная) ---

    @staticmethod
    def generate_boss_reactive_block(boss_id: int) -> list[str]:
        """
        Генерирует реактивный блок для босса.

        Эта функция вызывается в момент удара игрока, позволяя боссу
        "мгновенно" среагировать на атаку.

        Args:
            boss_id (int): ID босса.

        Returns:
            list[str]: Список зон, которые босс блокирует.
        """
        # Умный босс может закрывать 3 из 4 зон.
        all_zones = ["head", "chest", "legs", "feet"]
        block_zones = random.sample(all_zones, 3)
        log.debug(f"Босс {boss_id} реактивно блокирует: {block_zones}.")
        return block_zones

    @staticmethod
    def select_aggro_target(boss_data: dict, participants: dict) -> int:
        """
        Выбирает цель для специальной атаки босса на основе агро-таблицы.

        Args:
            boss_data (dict): Данные о состоянии босса.
            participants (dict): Словарь с данными всех участников боя.

        Returns:
            int: ID персонажа-цели. 0, если живых целей нет.
        """
        # 1. Фильтруем живых игроков из команды "blue" (команда игроков).
        living_players = [
            p_id
            for p_id, p_data in participants.items()
            if p_data["team"] == "blue" and p_data["state"]["hp_current"] > 0
        ]

        if not living_players:
            log.warning("Босс не нашел живых целей для атаки.")
            return 0

        # TODO: Реализовать логику выбора цели на основе уровня угрозы (Aggro).
        # В данный момент цель выбирается случайно.
        target_id = int(random.choice(living_players))
        log.debug(f"Босс выбрал цель для спец-удара: {target_id}.")
        return target_id
