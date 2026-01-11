"""
Пакет DTO (Data Transfer Objects) для обмена данными между слоями приложения.
Экспортирует основные DTO для удобного импорта.
"""

# Character DTOs
from .character_dto import (
    CharacterAttributesReadDTO,
    CharacterAttributesUpdateDTO,
    CharacterOnboardingUpdateDTO,
    CharacterReadDTO,
    CharacterShellCreateDTO,
    CharacterStatsReadDTO,  # Alias
    CharacterStatsUpdateDTO,  # Alias
)

# Combat DTOs
from .combat_source_dto import (
    ActorFullInfo,
    ActorShortInfo,
    CombatDashboardDTO,
    CombatLogDTO,
    CombatLogEntryDTO,
    CombatMoveDTO,
)

# Inventory & Item DTOs
from .inventory_dto import (
    InventoryBagResponseDTO,
    InventoryItemDetailsResponseDTO,
    InventoryMainMenuResponseDTO,
    InventorySessionDTO,
    WalletDTO,
)
from .item_dto import (
    EquippedSlot,
    InventoryItemDTO,
    ItemRarity,
    ItemType,
    QuickSlot,
)

# Skill DTOs
from .skill import (
    SkillDisplayDTO,
    SkillProgressDTO,
)

# User DTOs
from .user_dto import (
    UserDTO,
    UserUpsertDTO,
)

__all__ = [
    # Character
    "CharacterAttributesReadDTO",
    "CharacterAttributesUpdateDTO",
    "CharacterOnboardingUpdateDTO",
    "CharacterReadDTO",
    "CharacterShellCreateDTO",
    "CharacterStatsReadDTO",
    "CharacterStatsUpdateDTO",
    # Combat
    "ActorFullInfo",
    "ActorShortInfo",
    "CombatDashboardDTO",
    "CombatLogDTO",
    "CombatLogEntryDTO",
    "CombatMoveDTO",
    # Inventory & Items
    "InventoryBagResponseDTO",
    "InventoryItemDetailsResponseDTO",
    "InventoryMainMenuResponseDTO",
    "InventorySessionDTO",
    "WalletDTO",
    "EquippedSlot",
    "InventoryItemDTO",
    "ItemRarity",
    "ItemType",
    "QuickSlot",
    # Skill
    "SkillDisplayDTO",
    "SkillProgressDTO",
    # User
    "UserDTO",
    "UserUpsertDTO",
]
