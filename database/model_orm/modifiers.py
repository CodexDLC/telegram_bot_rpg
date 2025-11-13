# database/model_orm/modifiers.py
from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.model_orm.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .character import Character


class CharacterModifiers(Base, TimestampMixin):
    """
    ORM-модель для таблицы `character_modifiers`.

    Хранит все вычисляемые модификаторы и бонусы для персонажа.
    Эти значения являются производными от характеристик, навыков, экипировки
    и временных эффектов. Связана с `Character` отношением "один-к-одному".

    Attributes:
        character_id (Mapped[int]): ID персонажа (первичный и внешний ключ).
        ... (атрибуты модификаторов) ...
        character (Mapped["Character"]): Обратная связь с моделью Character.
    """
    __tablename__ = "character_modifiers"

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        primary_key=True
    )

    # --- Физические боевые модификаторы ---
    physical_damage_bonus: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    physical_penetration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    physical_crit_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    physical_crit_power_float: Mapped[float] = mapped_column(Float, default=1.5, nullable=False)
    physical_crit_power_int: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    physical_crit_chance_cap: Mapped[float] = mapped_column(Float, default=0.75, nullable=False)

    # --- Магические боевые модификаторы ---
    magical_damage_bonus: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    magical_penetration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    magical_crit_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    magical_crit_power_float: Mapped[float] = mapped_column(Float, default=1.5, nullable=False)
    magical_crit_power_int: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    magical_crit_chance_cap: Mapped[float] = mapped_column(Float, default=0.50, nullable=False)
    spell_land_chance: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    magical_accuracy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # --- Общие боевые модификаторы ---
    counter_attack_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    pet_ally_power: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    vampiric_rage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    parry_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # --- Ресурсы ---
    hp_max: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hp_regen: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    energy_max: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    energy_regen: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # --- Защитные модификаторы ---
    dodge_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    anti_dodge: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    debuff_avoidance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    shield_block_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    shield_block_power: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    physical_resistance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    control_resistance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    magical_resistance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    anti_physical_crit_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    anti_magical_crit_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    shock_resistance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # --- Экипировка хрант кубик дрони в формате 1d3 или 2d6  ---
    armor_shield: Mapped[str] = mapped_column(String(100), nullable=True)
    armor_head: Mapped[str] = mapped_column(String(100), nullable=True)
    armor_chest: Mapped[str] = mapped_column(String(100), nullable=True)
    armor_legs: Mapped[str] = mapped_column(String(100), nullable=True)
    armor_feet: Mapped[str] = mapped_column(String(100), nullable=True)

    # --- Утилитарные и экономические модификаторы ---
    received_healing_bonus: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trade_discount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    find_loot_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    crafting_critical_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    skill_gain_bonus: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    crafting_success_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    inventory_slots_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # --- Связь ---
    character: Mapped["Character"] = relationship(back_populates="modifiers")

    def __repr__(self) -> str:
        return f"<CharacterModifiers(character_id={self.character_id})>"
