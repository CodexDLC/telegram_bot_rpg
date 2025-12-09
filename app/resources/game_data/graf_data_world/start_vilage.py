from typing import Any, TypedDict


class _StaticLocationContent(TypedDict):
    title: str
    description: str
    environment_tags: list[str]


class _StaticLocation(TypedDict):
    sector_id: str
    is_active: bool
    service_object_key: str | None
    flags: dict[str, Any]
    content: _StaticLocationContent


# ==============================================================================
# СТАТИЧНЫЕ ЛОКАЦИИ (Центральный Хаб в "Римском" стиле)
# ==============================================================================
STATIC_LOCATIONS: dict[tuple[int, int], _StaticLocation] = {
    # ---------------------------------------------------------
    # ЦЕНТР И ОСИ (КРЕСТ) - Точки входа в сервисы
    # ---------------------------------------------------------
    (52, 52): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "is_hub": True, "has_road": True},
        "content": {
            "title": "Портальный Круг",
            "description": "Земля здесь выжжена до черноты магией Портала. Вокруг древних камней разбросаны палатки карантинной зоны.",
            "environment_tags": ["portal", "safe_zone", "camp"],
        },
    },
    (52, 51): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": "svc_arena_main",
        "flags": {"is_safe_zone": True, "has_road": True},
        "content": {
            "title": "Тренировочная площадка",
            "description": "Утоптанная земля, окруженная самодельными мишенями. Впереди виднеется вход в большой ангар, где проходят бои.",
            "environment_tags": ["arena_outer", "training", "military"],
        },
    },
    (52, 53): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": "taverna_hub",
        "flags": {"is_safe_zone": True, "has_road": True},
        "content": {
            "title": "Двор 'Едальни'",
            "description": "Площадка перед бараком-столовой. На кострах жарится мясо, люди отдыхают после смен.",
            "environment_tags": ["yard", "bonfire", "cooking"],
        },
    },
    (51, 52): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": "town_hall_hub",
        "flags": {"is_safe_zone": True, "has_road": True},
        "content": {
            "title": "Палатка Совета",
            "description": "Большой армейский шатер, служащий временной администрацией. Рядом доска с объявлениями.",
            "environment_tags": ["official", "tent", "notice_board"],
        },
    },
    (53, 52): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": "market_hub",
        "flags": {"is_safe_zone": True, "has_road": True},
        "content": {
            "title": "Рынок 'Барахолка'",
            "description": "Стихийный рынок, где торговля идет прямо с ящиков и расстеленных на земле покрывал.",
            "environment_tags": ["market", "mud", "barter"],
        },
    },
    # ---------------------------------------------------------
    # УГЛОВЫЕ УЧАСТКИ (пока пустые, в будущем под застройку)
    # ---------------------------------------------------------
    (51, 51): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "has_road": True},
        "content": {
            "title": "Пустой участок (С-З)",
            "description": "Размеченный колышками кусок грязной земли. Пока что здесь сваливают мусор, но кто-то явно присматривает это место для будущего строительства.",
            "environment_tags": ["mud", "unclaimed_land", "debris"],
        },
    },
    (53, 51): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "has_road": True},
        "content": {
            "title": "Пустой участок (С-В)",
            "description": "Угловой участок, заваленный ящиками и старыми бочками. Похоже, его используют как временный склад.",
            "environment_tags": ["mud", "unclaimed_land", "storage"],
        },
    },
    (51, 53): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "has_road": True},
        "content": {
            "title": "Пустой участок (Ю-З)",
            "description": "Ничем не примечательный пустырь. Земля утоптана множеством ног, но ничего не построено.",
            "environment_tags": ["mud", "unclaimed_land", "empty"],
        },
    },
    (53, 53): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "has_road": True},
        "content": {
            "title": "Пустой участок (Ю-В)",
            "description": "Здесь кто-то пытался разбить огород, но остались лишь сухие грядки. Место свободно.",
            "environment_tags": ["mud", "unclaimed_land", "garden"],
        },
    },
    # ---------------------------------------------------------
    # ПЕРИМЕТР (Римский вал, ров и частокол)
    # ---------------------------------------------------------
    (52, 50): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": False, "is_gate": True},
        "content": {
            "title": "Северные Ворота",
            "description": "Тяжелые, сколоченные из мусора и арматуры ворота. Их охраняет суровый патруль, явно из 'старой гвардии'.",
            "environment_tags": ["gate", "defense", "roman_style"],
        },
    },
    (50, 50): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["north", "west"], "has_road": True},
        "content": {
            "title": "Северо-Западный Бастион",
            "description": "Здесь сходятся северный и западный валы. С самодельной вышки дозорный осматривает окрестности.",
            "environment_tags": ["bastion", "fortification", "roman_style"],
        },
    },
    (51, 50): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["north"], "has_road": True},
        "content": {
            "title": "Северный Вал",
            "description": "Перед вами — свежевырытый ров и земляной вал, утыканный заостренными кольями. Дисциплина легионеров чувствуется даже здесь.",
            "environment_tags": ["rampart", "ditch", "fortification", "roman_style"],
        },
    },
    (53, 50): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["north"], "has_road": True},
        "content": {
            "title": "Северный Вал",
            "description": "Высокий земляной вал, укрепленный листами ржавого металла. Надежная защита, построенная первыми поселенцами.",
            "environment_tags": ["rampart", "fortification", "roman_style"],
        },
    },
    (54, 50): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["north", "east"], "has_road": True},
        "content": {
            "title": "Северо-Восточный Бастион",
            "description": "Угловая точка обороны лагеря. На вышке виден силуэт часового.",
            "environment_tags": ["bastion", "fortification", "roman_style"],
        },
    },
    (50, 54): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["south", "west"], "has_road": True},
        "content": {
            "title": "Юго-Западный Бастион",
            "description": "Угловая точка обороны лагеря. Отсюда хорошо просматриваются подходы с юга и запада.",
            "environment_tags": ["bastion", "fortification", "roman_style"],
        },
    },
    (51, 54): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["south"], "has_road": True},
        "content": {
            "title": "Южный Вал",
            "description": "Земляной вал, за которым начинается болотистая низина.",
            "environment_tags": ["rampart", "fortification", "roman_style"],
        },
    },
    (52, 54): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": False, "is_gate": True},
        "content": {
            "title": "Южные Ворота",
            "description": "Скрипучие ворота, ведущие к болотам. Охраняются не так усердно, как северные.",
            "environment_tags": ["gate", "defense"],
        },
    },
    (53, 54): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["south"], "has_road": True},
        "content": {
            "title": "Южный Вал",
            "description": "Наспех возведенный вал, защищающий от тварей с болот.",
            "environment_tags": ["rampart", "fortification", "roman_style"],
        },
    },
    (54, 54): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["south", "east"], "has_road": True},
        "content": {
            "title": "Юго-Восточный Бастион",
            "description": "Угловая вышка, с которой часовой наблюдает за руинами на востоке.",
            "environment_tags": ["bastion", "fortification", "roman_style"],
        },
    },
    (50, 51): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["west"], "has_road": True},
        "content": {
            "title": "Западный Вал",
            "description": "Высокий земляной вал, укрепленный бетонными плитами из руин.",
            "environment_tags": ["rampart", "fortification", "roman_style"],
        },
    },
    (50, 52): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": False, "is_gate": True},
        "content": {
            "title": "Западные Ворота",
            "description": "Технические ворота, через которые вывозят мусор. Почти не охраняются.",
            "environment_tags": ["gate", "defense"],
        },
    },
    (50, 53): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["west"], "has_road": True},
        "content": {
            "title": "Западный Вал",
            "description": "Надежное укрепление, построенное по всем правилам военной науки.",
            "environment_tags": ["rampart", "fortification", "roman_style"],
        },
    },
    (54, 51): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["east"], "has_road": True},
        "content": {
            "title": "Восточный Частокол",
            "description": "Частокол из заостренных бревен, за которым виднеются руины старого мира.",
            "environment_tags": ["palisade", "fortification", "roman_style"],
        },
    },
    (54, 52): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": False, "is_gate": True},
        "content": {
            "title": "Восточные Ворота",
            "description": "Небольшая калитка в частоколе, ведущая к руинам.",
            "environment_tags": ["gate", "defense"],
        },
    },
    (54, 53): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["east"], "has_road": True},
        "content": {
            "title": "Восточный Частокол",
            "description": "Прочный частокол, защищающий от тварей из руин.",
            "environment_tags": ["palisade", "fortification", "roman_style"],
        },
    },
}
