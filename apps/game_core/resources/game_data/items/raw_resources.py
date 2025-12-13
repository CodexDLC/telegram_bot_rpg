from typing import TypedDict


class ResourceData(TypedDict):
    id: str
    name_ru: str
    base_price: int
    narrative_description: str  # Для UI "Осмотреть"


# Структура: Категория -> Тир -> Данные
RAW_RESOURCES_DB: dict[str, dict[int, ResourceData]] = {
    # === РУДЫ (Для плавки в слитки) ===
    "ores": {
        0: {
            "id": "res_rust_flakes",
            "name_ru": "Ржавая труха",
            "base_price": 1,
            "narrative_description": "Осыпавшаяся ржавчина. Бесполезна.",
        },
        1: {
            "id": "res_iron_ore",
            "name_ru": "Железная руда",
            "base_price": 5,
            "narrative_description": "Тяжелый кусок породы с прожилками железа.",
        },
        # 2: res_coal_ore (Сталь требует угля + железа), но пока упростим
    },
    # === ШКУРЫ (Для дубления в кожу) ===
    "hides": {
        0: {
            "id": "res_torn_pelt",
            "name_ru": "Дырявая шкура",
            "base_price": 1,
            "narrative_description": "Шкура, испорченная паразитами.",
        },
        1: {
            "id": "res_wolf_pelt",
            "name_ru": "Волчья шкура",
            "base_price": 4,
            "narrative_description": "Грубая шерсть серого волка.",
        },
    },
    # === ЭССЕНЦИИ (Для магии/Бандлов) ===
    # У эссенций Тир = минимальный тир предмета, в который её можно вставить
    "essences": {
        1: {
            "id": "essence_shadow_dust",
            "name_ru": "Пыль Теней",
            "base_price": 20,
            "narrative_description": "Странный порошок, делающий предметы легкими и незаметными.",
        },
        2: {
            "id": "essence_blood_vial",
            "name_ru": "Флакон Крови",
            "base_price": 50,
            "narrative_description": "Густая, теплая кровь. Кажется, она живая.",
        },
    },
}
