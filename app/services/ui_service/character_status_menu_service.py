#app/services/ui_service/character_status_menu_service.py

import logging
from aiogram.types import InlineKeyboardMarkup
from typing import Tuple, Dict, Any, List, Optional

# Импорты DTO
from app.resources.schemas_dto.character_dto import CharacterReadDTO
from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO
from app.resources.schemas_dto.skill import SkillProgressDTO

# Импорты хелперов и форматтеров
from app.services.helpers_module.ui.lobby_formatters import LobbyFormatter
from app.resources.keyboards.inline_kb.loggin_und_new_character import get_character_data_bio

# ... Импорты других хелперов, например, SkillCalculatorService

log = logging.getLogger(__name__)


class CharacterMenuUIService:
    """
    Фасад Отображения. Его единственная задача — принять DTO и вернуть (текст, клавиатуру).
    Он не лезет в БД. Он скрывает логику форматирования и выбора клавиатуры.
    """

