"""
Обработчики, связанные с использованием способностей (умений) в бою.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.resources.fsm_states.states import InGame
from app.resources.keyboards.combat_callback import CombatActionCallback

ability_router = Router(name="combat_abilities")


@ability_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action.regexp(r"skill_use:(\w+)")))
async def handle_skill_use(call: CallbackQuery, callback_data: CombatActionCallback):
    # TODO: [Temporary] Заменить ненадежный split на специальный CombatAbilityCallback
    # class CombatAbilityCallback(CallbackData, prefix="c_abil"):
    #     skill_key: str
    skill_key = callback_data.action.split(":")[1]
    # TODO: Добавить логику использования скилла через CombatService
    await call.answer(f"Используем скилл: {skill_key} (WIP)", show_alert=True)
