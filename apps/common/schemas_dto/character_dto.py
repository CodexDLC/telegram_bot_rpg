"""
Модуль содержит DTO (Data Transfer Objects) для работы с персонажами.

Определяет структуры данных для создания "оболочки" персонажа,
обновления данных после онбординга, чтения полной информации о персонаже,
а также для обновления и чтения его характеристик.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Gender = Literal["male", "female", "other"]  # Возможные значения для пола персонажа.


class CharacterShellCreateDTO(BaseModel):
    """
    DTO для создания "оболочки" персонажа.
    Содержит только идентификатор пользователя Telegram, который создает персонажа.
    """

    user_id: int  # Уникальный идентификатор пользователя Telegram.


class CharacterOnboardingUpdateDTO(BaseModel):
    """
    DTO для обновления данных персонажа после прохождения онбординга.
    Используется для сохранения имени, пола и текущей стадии игры.
    """

    name: str  # Имя персонажа, выбранное игроком.
    gender: Gender  # Пол персонажа ("male", "female", "other").
    game_stage: str  # Текущая стадия игры персонажа (например, "creation", "in_game").


class CharacterReadDTO(BaseModel):
    """
    DTO для чтения полной информации о персонаже из базы данных.
    Включает все основные атрибуты персонажа.
    """

    character_id: int  # Уникальный идентификатор персонажа в игре.
    user_id: int  # Идентификатор пользователя Telegram, которому принадлежит персонаж.
    name: str  # Имя персонажа.
    gender: Gender  # Пол персонажа.
    game_stage: str  # Текущая стадия игры персонажа.
    created_at: datetime  # Дата и время создания персонажа.
    updated_at: datetime  # Дата и время последнего обновления данных персонажа.

    model_config = ConfigDict(from_attributes=True)


class CharacterStatsUpdateDTO(BaseModel):
    """
    DTO для обновления характеристик персонажа.
    Используется для изменения базовых характеристик.
    """

    strength: int  # Сила: влияет на физический урон, переносимый вес.
    agility: int  # Ловкость: влияет на уклонение, точность, скорость атаки.
    endurance: int  # Выносливость: влияет на максимальное HP, физическое сопротивление.
    intelligence: int  # Интеллект: влияет на магический урон, эффективность заклинаний.
    wisdom: int  # Мудрость: влияет на магическое сопротивление, шанс крита заклинаний.
    men: int  # Дух: влияет на максимальную энергию/ману, сопротивление контролю.
    perception: int  # Восприятие: влияет на шанс найти лут, обнаружение ловушек, слоты инвентаря.
    charisma: int  # Харизма: влияет на цены у торговцев, эффективность питомцев, социальные навыки.
    luck: int  # Удача: влияет на шанс крита, шанс найти лут, успех крафта.


class CharacterStatsReadDTO(CharacterStatsUpdateDTO):
    """
    DTO для чтения характеристик персонажа из базы данных.
    Включает поля из `CharacterStatsUpdateDTO` и временные метки.
    """

    created_at: datetime  # Дата и время создания записи характеристик.
    updated_at: datetime  # Дата и время последнего обновления записи характеристик.

    model_config = ConfigDict(from_attributes=True)
