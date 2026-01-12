from collections import defaultdict

from loguru import logger as log

from apps.game_core.resources.game_data.gifts.definitions.darkness import DARKNESS_GIFTS
from apps.game_core.resources.game_data.gifts.definitions.fire import FIRE_GIFTS
from apps.game_core.resources.game_data.gifts.definitions.light import LIGHT_GIFTS
from apps.game_core.resources.game_data.gifts.definitions.nature import NATURE_GIFTS
from apps.game_core.resources.game_data.gifts.definitions.water import WATER_GIFTS
from apps.game_core.resources.game_data.gifts.schemas import GiftDTO, GiftSchool
from apps.game_core.resources.game_data.gifts.xp_config import GIFT_LEVELING

# ==========================================
# ГЛОБАЛЬНЫЕ РЕЕСТРЫ (In-Memory DB)
# ==========================================

GIFT_REGISTRY: dict[str, GiftDTO] = {}
GIFTS_BY_SCHOOL: dict[GiftSchool, list[GiftDTO]] = defaultdict(list)


def _register_gifts(gift_list: list[GiftDTO]) -> None:
    for gift in gift_list:
        if gift.gift_id in GIFT_REGISTRY:
            log.warning(f"GiftLibrary | Duplicate gift ID: '{gift.gift_id}'. Overwriting.")

        GIFT_REGISTRY[gift.gift_id] = gift
        GIFTS_BY_SCHOOL[gift.school].append(gift)


def _initialize_library() -> None:
    log.info("GiftLibrary | Initializing Gift Library...")

    all_gifts = [FIRE_GIFTS, WATER_GIFTS, LIGHT_GIFTS, DARKNESS_GIFTS, NATURE_GIFTS]

    count = 0
    for group in all_gifts:
        _register_gifts(group)
        count += len(group)

    log.info(f"GiftLibrary | Initialization complete. Loaded {count} gifts.")


# ==========================================
# PUBLIC API
# ==========================================


def get_gift_config(gift_id: str) -> GiftDTO | None:
    return GIFT_REGISTRY.get(gift_id)


def get_all_gifts() -> list[GiftDTO]:
    return list(GIFT_REGISTRY.values())


def get_gifts_by_school(school: GiftSchool) -> list[GiftDTO]:
    return GIFTS_BY_SCHOOL.get(school, [])


def get_gift_level_info(level: int) -> dict | None:
    return GIFT_LEVELING.get(level)


# Auto-init
_initialize_library()
