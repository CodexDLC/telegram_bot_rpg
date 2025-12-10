# app/resources/game_data/abilities/__init__.py
from apps.game_core.resources.game_data.ability_data_struct import AbilityData

# Импортируем словари из соседних модулей
from .fire import FIRE_ABILITIES
from .physical import PHYSICAL_ABILITIES
from .poison import POISON_ABILITIES

# Объединяем их в единую библиотеку
ABILITY_LIBRARY: dict[str, AbilityData] = PHYSICAL_ABILITIES | FIRE_ABILITIES | POISON_ABILITIES

# Проверка на уникальность ключей (опционально, для отладки при старте)
# Если ключи совпадут, правый словарь перезапишет левый.
