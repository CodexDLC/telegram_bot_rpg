from typing import TypedDict


class MaterialStats(TypedDict):
    id: str
    name_ru: str
    tier_mult: float  # ГЛАВНОЕ: Множитель всей силы предмета
    slots: int  # Емкость для магии
    narrative_tags: list[str]  # Теги для LLM ("rusty", "shining", "void")


# Структура: Категория -> Тир -> Данные
CRAFTING_MATERIALS_DB: dict[str, dict[int, MaterialStats]] = {
    # === МЕТАЛЛЫ (Ingots) ===
    "ingots": {
        0: {
            "id": "mat_scrap_metal",
            "name_ru": "Ржавый лом",
            "tier_mult": 0.8,  # Штраф 20% к статам базы
            "slots": 0,  # Никакой магии
            "narrative_tags": ["rusty", "junk", "old", "brittle"],
        },
        1: {
            "id": "mat_iron_ingot",
            "name_ru": "Железо",
            "tier_mult": 1.0,  # База
            "slots": 1,  # 1 слот под мелкую магию
            "narrative_tags": ["iron", "heavy", "dull_grey", "reliable"],
        },
        2: {
            "id": "mat_steel_ingot",
            "name_ru": "Сталь",
            "tier_mult": 1.5,
            "slots": 2,
            "narrative_tags": ["steel", "polished", "sharp", "tempered"],
        },
        # ... Mithril (Tier 3), Adamantite (Tier 4), Void (Tier 5)
    },
    # === КОЖА (Leathers) ===
    "leathers": {
        0: {
            "id": "mat_torn_leather",
            "name_ru": "Лохмотья",
            "tier_mult": 0.8,
            "slots": 0,
            "narrative_tags": ["torn", "rotten", "smelly"],
        },
        1: {
            "id": "mat_cured_leather",
            "name_ru": "Дубленая кожа",
            "tier_mult": 1.0,
            "slots": 1,
            "narrative_tags": ["leather", "brown", "tough"],
        },
        2: {
            "id": "mat_thick_leather",
            "name_ru": "Толстая кожа",
            "tier_mult": 1.4,  # Чуть меньше стали
            "slots": 2,
            "narrative_tags": ["thick", "reinforced", "beast_hide"],
        },
    },
    # === ТКАНИ (Cloths) ===
    "cloths": {
        0: {
            "id": "mat_dirty_rags",
            "name_ru": "Грязное тряпье",
            "tier_mult": 0.8,
            "slots": 0,
            "narrative_tags": ["dirty", "rags", "cloth"],
        },
        1: {
            "id": "mat_linen",
            "name_ru": "Лен",
            "tier_mult": 1.0,
            "slots": 2,  # Ткань лучше держит магию, чем железо (балансная фишка)
            "narrative_tags": ["linen", "clean", "white"],
        },
        2: {
            "id": "mat_silk",
            "name_ru": "Шелк",
            "tier_mult": 1.3,
            "slots": 3,
            "narrative_tags": ["silk", "soft", "expensive"],
        },
    },
}
