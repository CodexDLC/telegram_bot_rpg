class CombatSessionFields:
    """
    Константы полей для метаданных боевой сессии (RBC).
    Ключ Redis: combat:rbc:{session_id}:meta
    """

    # Статус и время
    ACTIVE = "active"  # 1 - бой идет, 0 - завершен
    START_TIME = "start_time"  # Timestamp начала
    END_TIME = "end_time"  # Timestamp завершения
    WINNER = "winner"  # Победившая команда ("red", "blue")

    # Структурные данные (JSON)
    TEAMS = "teams"  # Распределение по командам {team: [ids]}
    ACTORS_INFO = "actors_info"  # Роли участников {id: "player"|"ai"}
    DEAD_ACTORS = "dead_actors"  # Список мертвых [ids]
    REWARDS = "rewards"  # Рассчитанные награды {id: {xp, gold...}}

    # Конфигурация (копируется из конфига боя)
    BATTLE_TYPE = "battle_type"  # "pve", "pvp"
    MODE = "mode"  # "1v1", "group", "dungeon"
    IS_PVE = "is_pve"  # Флаг PVE (для удобства)
    LOCATION_ID = "location_id"  # Локация, где идет бой


class CombatActorFields:
    """
    Константы для полей внутри состояния актора.
    В текущей реализации RBC состояние актора хранится как единый JSON,
    но эти ключи используются при формировании словарей для DTO.
    """

    HP_CURRENT = "hp_current"
    ENERGY_CURRENT = "energy_current"
    TARGETS = "targets"
    SWITCH_CHARGES = "switch_charges"
