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
    physical_damage_bonus: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Бонусный % физ. урона
    physical_penetration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # % игнорирования физ. брони цели
    physical_crit_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Шанс нанести критический физ. урон
    physical_crit_power_float: Mapped[float] = mapped_column(Float, default=1.5, nullable=False)  # Множитель физ. крит. урона (e.g., 1.5 = 150%)
    physical_crit_power_int: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Дополнительный плоский физ. крит. урон
    physical_crit_chance_cap: Mapped[float] = mapped_column(Float, default=0.75, nullable=False)  # Максимальный предел шанса физ. крита

    # --- Магические боевые модификаторы ---
    magical_damage_bonus: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Бонусный % маг. урона
    magical_penetration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # % игнорирования маг. сопротивления цели
    magical_crit_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Шанс нанести критический маг. урон
    magical_crit_power_float: Mapped[float] = mapped_column(Float, default=1.5, nullable=False)  # Множитель маг. крит. урона
    magical_crit_power_int: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Дополнительный плоский маг. крит. урон
    magical_crit_chance_cap: Mapped[float] = mapped_column(Float, default=0.50, nullable=False)  # Максимальный предел шанса маг. крита
    spell_land_chance: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)  # Шанс успешного наложения эффекта (дебаффа)
    magical_accuracy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Противодействует уклонению от заклинаний

    # --- Общие боевые модификаторы ---
    counter_attack_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Шанс провести контратаку после атаки врага
    pet_ally_power: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # % усиления урона и здоровья питомцев/союзников
    vampiric_rage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # % нанесенного урона, который преобразуется в здоровье
    parry_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Шанс парировать атаку, полностью избежав урона

    # --- Ресурсы ---
    hp_max: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Максимальное количество очков здоровья
    hp_regen: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Количество здоровья, восстанавливаемое в единицу времени
    energy_max: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Максимальное количество очков энергии/маны
    energy_regen: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Количество энергии, восстанавливаемое в единицу времени

    # --- Защитные модификаторы ---
    dodge_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Шанс полностью уклониться от физической атаки
    anti_dodge: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Снижает шанс уклонения противника
    debuff_avoidance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Шанс избежать наложения негативных эффектов
    shield_block_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Шанс заблокировать атаку щитом
    shield_block_power: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # % поглощаемого урона при блоке щитом
    physical_resistance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # % снижения входящего физического урона
    control_resistance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # % сопротивления эффектам контроля (оглушение, сон)
    magical_resistance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # % снижения входящего магического урона
    anti_physical_crit_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Снижает шанс противника нанести физ. крит
    anti_magical_crit_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Снижает шанс противника нанести маг. крит
    shock_resistance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Сопротивление шоку (вероятно, прерыванию действий)

    # --- Экипировка (хранит "кубик" брони в формате 1d3 или 2d6) ---
    armor_shield: Mapped[str] = mapped_column(String(100), nullable=True)  # Значение поглощения урона щитом
    armor_head: Mapped[str] = mapped_column(String(100), nullable=True)  # Значение брони для головы
    armor_chest: Mapped[str] = mapped_column(String(100), nullable=True)  # Значение брони для тела
    armor_legs: Mapped[str] = mapped_column(String(100), nullable=True)  # Значение брони для ног
    armor_feet: Mapped[str] = mapped_column(String(100), nullable=True)  # Значение брони для ступней

    # --- Утилитарные и экономические модификаторы ---
    received_healing_bonus: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # % увеличения получаемого исцеления
    trade_discount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # % скидки у торговцев
    find_loot_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # % увеличения шанса найти добычу
    crafting_critical_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Шанс создать предмет исключительного качества
    skill_gain_bonus: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # % бонуса к получаемому опыту навыков
    crafting_success_chance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Шанс успешного создания предмета
    inventory_slots_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Дополнительные ячейки в инвентаре

    # --- Связь ---
    character: Mapped["Character"] = relationship(back_populates="modifiers")

    def __repr__(self) -> str:
        return f"<CharacterModifiers(character_id={self.character_id})>"


