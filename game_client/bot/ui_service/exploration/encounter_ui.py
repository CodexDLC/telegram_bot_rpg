# apps/bot/ui_service/exploration/encounter_ui.py

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.common.schemas_dto.exploration_dto import DetectionStatus, EncounterDTO
from game_client.bot.resources.keyboards.callback_data import EncounterCallback
from game_client.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO


class EncounterUI:
    """
    UI-компонент для отображения случайных встреч.
    """

    @staticmethod
    def render_combat_preview(dto: EncounterDTO) -> ViewResultDTO:
        """
        Отрисовка превью боя в зависимости от статуса обнаружения.
        """
        if dto.status == DetectionStatus.DETECTED:
            text = f"👁 <b>УГРОЗА ОБНАРУЖЕНА</b>\n\nВпереди вы замечаете: <b>{dto.name}</b>.\n<i>{dto.description}</i>"
            kb = EncounterUI._get_detected_kb(dto.encounter_id)

        elif dto.status == DetectionStatus.AMBUSH:
            text = f"⚔️ <b>ЗАСАДА!</b>\n\n<i>{dto.description}</i>\nБой неизбежен."
            kb = EncounterUI._get_ambush_kb(dto.encounter_id)

        else:
            text = f"Вы столкнулись с {dto.name}."
            kb = None

        return ViewResultDTO(text=text, kb=kb)

    @staticmethod
    def render_narrative(dto: EncounterDTO) -> ViewResultDTO:
        text = f"📜 <b>{dto.name.upper()}</b>\n\n{dto.description}"
        kb = EncounterUI._get_narrative_kb(dto.encounter_id)
        return ViewResultDTO(text=text, kb=kb)

    @staticmethod
    def _get_detected_kb(target_id: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text="⚔️ Атаковать", callback_data=EncounterCallback(action="attack", target_id=target_id).pack())
        builder.button(text="👣 Обойти", callback_data=EncounterCallback(action="bypass", target_id=target_id).pack())
        builder.adjust(2)
        return builder.as_markup()

    @staticmethod
    def _get_ambush_kb(target_id: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text="🛡 В бой!", callback_data=EncounterCallback(action="attack", target_id=target_id).pack())
        return builder.as_markup()

    @staticmethod
    def _get_narrative_kb(target_id: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="🔍 Осмотреть", callback_data=EncounterCallback(action="inspect", target_id=target_id).pack()
        )
        builder.button(text="➡️ Уйти", callback_data=EncounterCallback(action="bypass", target_id=target_id).pack())
        builder.adjust(2)
        return builder.as_markup()
