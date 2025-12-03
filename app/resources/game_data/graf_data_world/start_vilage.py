WORLD_DATA = {
    "portal_plats": {
        "title": "Портальный Круг",
        "description": (
            "Земля здесь выжжена до черноты пульсирующей магией Портала. "
            "Вокруг древних камней хаотично разбросаны палатки карантинной зоны. "
            "Вновь прибывшие сидят на ящиках, кутаясь в пледы. "
            "Здесь пахнет озоном и лекарствами. На севере слышны команды инструкторов и лязг металла."
        ),
        "environment_tags": ["portal", "safe_zone", "camp"],
        "exits": {
            "market_square": {
                "desc_next_room": "На востоке видны ряды пестрых палаток.",
                "time_duration": 4,
                "text_button": "Рынок (Восток)",
            },
            "town_hall_square": {
                "desc_next_room": "На западе стоит здание штаба Совета.",
                "time_duration": 4,
                "text_button": "Штаб (Запад)",
            },
            # ИЗМЕНЕНИЕ: Север теперь ведет к Полигону, а не сразу к Воротам
            "training_ground_entrance": {
                "desc_next_room": "На севере разбит военный лагерь и тренировочная зона.",
                "time_duration": 3,
                "text_button": "К Полигону (Север)",
            },
            "taverna_yard": {
                "desc_next_room": "С юга доносится запах еды.",
                "time_duration": 4,
                "text_button": "Таверна (Юг)",
            },
        },
    },
    # --- ЛОКАЦИЯ ПЕРЕНЕСЕНА БЛИЖЕ К ЦЕНТРУ ---
    "training_ground_entrance": {
        "title": "Военный Плац",
        "description": (
            "Буферная зона между центром лагеря и внешней стеной. "
            "Здесь инструкторы муштруют новичков, готовя их к рейдам. "
            "В центре стоит массивный ангар 'АРЕНА' для спаррингов. "
            "Дальше на север виднеются главные ворота поселения."
        ),
        "environment_tags": ["arena_outer", "training", "military"],
        "exits": {
            "portal_plats": {
                "desc_next_room": "Вернуться к Порталу.",
                "time_duration": 3,
                "text_button": "В центр (Юг)",
            },
            "svc_arena_main": {
                "desc_next_room": "Войти в ангар для регистрации боев.",
                "time_duration": 1,
                "text_button": "Войти в Арену",
            },
            "settlement_gates": {
                "desc_next_room": "Подойти к внешней стене и воротам.",
                "time_duration": 3,
                "text_button": "К Воротам (Север)",
            },
        },
    },
    # --- ТЕПЕРЬ ВОРОТА НАХОДЯТСЯ ЗА ПОЛИГОНОМ ---
    "settlement_gates": {
        "title": "Северный Частокол",
        "description": (
            "Стена из заостренных бревен, граница безопасности. "
            "Дозорные на вышках смотрят в сторону леса. "
            "Чтобы вернуться в жилую зону, нужно пройти через плац."
        ),
        "environment_tags": ["gate", "defense", "danger"],
        "exits": {
            "training_ground_entrance": {
                "desc_next_room": "Вернуться на военный плац.",
                "time_duration": 3,
                "text_button": "На Плац (Юг)",
            },
            "wild_lands": {
                "desc_next_room": "Выйти за периметр в туман.",
                "time_duration": 5,
                "text_button": "В Дикие Земли (ОПАСНО)",
            },
        },
    },
    # --- ОСТАЛЬНЫЕ ЛОКАЦИИ БЕЗ ИЗМЕНЕНИЙ ---
    "market_square": {
        "title": "Рынок 'Барахолка'",
        "description": (
            "Грязная площадь с торговыми рядами. "
            "Здесь меняют патроны на еду и артефакты. "
            "Шумно, людно, каждый пытается выторговать лишний паек."
        ),
        "environment_tags": ["market", "mud", "barter"],
        "exits": {
            "portal_plats": {
                "desc_next_room": "К Порталу.",
                "time_duration": 4,
                "text_button": "К Порталу",
            },
            "craftsman_alley": {
                "desc_next_room": "К ремесленникам.",
                "time_duration": 3,
                "text_button": "К Мастерам",
            },
        },
    },
    "craftsman_alley": {
        "title": "Зона Мастеров",
        "description": (
            "Дым самодельных горнов и стук молотков. Здесь чинят снаряжение и создают оружие из металлолома."
        ),
        "environment_tags": ["craft", "smoke", "survival"],
        "exits": {
            "market_square": {
                "desc_next_room": "На рынок.",
                "time_duration": 3,
                "text_button": "На Барахолку",
            },
        },
    },
    "taverna_yard": {
        "title": "Двор 'Едальни'",
        "description": ("Площадка перед бараком-столовой. На кострах жарится мясо, люди отдыхают после смен."),
        "environment_tags": ["yard", "bonfire", "cooking"],
        "exits": {
            "portal_plats": {
                "desc_next_room": "К Порталу.",
                "time_duration": 4,
                "text_button": "К Порталу",
            },
            "taverna_hall": {
                "desc_next_room": "Внутрь барака.",
                "time_duration": 2,
                "text_button": "В Таверну",
            },
        },
    },
    "taverna_hall": {
        "title": "Общий Зал",
        "description": ("Шумное, прокуренное помещение. Здесь едят, пьют и обсуждают вылазки."),
        "environment_tags": ["tavern", "indoor", "warm"],
        "exits": {
            "taverna_yard": {
                "desc_next_room": "На улицу.",
                "time_duration": 2,
                "text_button": "Во двор",
            },
            "taverna_cellar": {
                "desc_next_room": "В погреб.",
                "time_duration": 2,
                "text_button": "В склад",
            },
            "taverna_rooms": {
                "desc_next_room": "В спальни.",
                "time_duration": 2,
                "text_button": "В спальни",
            },
        },
    },
    "taverna_cellar": {
        "title": "Продуктовый Склад",
        "description": "Прохладная яма с припасами.",
        "environment_tags": ["dark", "storage", "food"],
        "exits": {
            "taverna_hall": {
                "desc_next_room": "Наверх.",
                "time_duration": 2,
                "text_button": "Наверх",
            },
        },
    },
    "taverna_rooms": {
        "title": "Спальный Отсек",
        "description": "Барак с нарами для сна.",
        "environment_tags": ["sleep", "bunk_beds", "quiet"],
        "exits": {
            "taverna_hall": {
                "desc_next_room": "В зал.",
                "time_duration": 2,
                "text_button": "В зал",
            },
        },
    },
    "town_hall_square": {
        "title": "Площадь Совета",
        "description": ("Плац перед Администрацией. Доска объявлений с заданиями и списками пропавших."),
        "environment_tags": ["official", "mud", "notice_board"],
        "exits": {
            "portal_plats": {
                "desc_next_room": "В центр.",
                "time_duration": 4,
                "text_button": "К Порталу",
            },
            "town_hall_interior": {
                "desc_next_room": "В штаб.",
                "time_duration": 2,
                "text_button": "В Штаб",
            },
            "library": {
                "desc_next_room": "В архив.",
                "time_duration": 2,
                "text_button": "В Архив",
            },
        },
    },
    "town_hall_interior": {
        "title": "Штаб Координации",
        "description": "Офис управления лагерем.",
        "environment_tags": ["official", "maps", "busy"],
        "exits": {
            "town_hall_square": {
                "desc_next_room": "На улицу.",
                "time_duration": 2,
                "text_button": "Выход",
            },
        },
    },
    "library": {
        "title": "Палатка Знаний",
        "description": "Склад книг и информации.",
        "environment_tags": ["books", "tent", "research"],
        "exits": {
            "town_hall_square": {
                "desc_next_room": "На улицу.",
                "time_duration": 2,
                "text_button": "Выход",
            },
        },
    },
    "svc_arena_main": {
        "title": "Ангар Арены",
        "description": "Центр матчмейкинга и регистрации боев.",
        "environment_tags": ["service_hub", "indoor"],
        "exits": {
            "training_ground_entrance": {
                "desc_next_room": "На улицу.",
                "time_duration": 2,
                "text_button": "На Плац",
            },
        },
    },
    "wild_lands": {
        "title": "Дикий Лес (Опушка)",
        "description": "Опасная территория за стеной.",
        "environment_tags": ["forest", "danger", "wild"],
        "exits": {
            "settlement_gates": {
                "desc_next_room": "Бежать к воротам.",
                "time_duration": 4,
                "text_button": "К Воротам",
            },
        },
    },
}
