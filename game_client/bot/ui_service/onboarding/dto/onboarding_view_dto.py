from dataclasses import dataclass

from aiogram.types import InlineKeyboardMarkup


@dataclass
class OnboardingViewDTO:
    """
    DTO для передачи готового UI от сервиса к хендлеру.
    """

    text: str
    keyboard: InlineKeyboardMarkup
