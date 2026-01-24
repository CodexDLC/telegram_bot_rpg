from typing import Any

from aiogram import Bot
from loguru import logger as log

from game_client.bot.core_client.status_client import StatusClient
from game_client.bot.resources.keyboards.status_callback import (
    StatusModifierCallback,
    StatusNavCallback,
    StatusSkillsCallback,
)
from game_client.bot.ui_service.helpers_ui.dto.ui_common_dto import MessageCoordsDTO, ViewResultDTO
from game_client.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY

# from apps.bot.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from game_client.bot.ui_service.status_menu.dto.status_view_dto import StatusViewDTO
from game_client.bot.ui_service.status_menu.status_modifier_service import CharacterModifierUIService
from game_client.bot.ui_service.status_menu.status_service import CharacterMenuUIService
from game_client.bot.ui_service.status_menu.status_skill_service import CharacterSkillStatusService


class StatusBotOrchestrator:
    def __init__(self, status_client: StatusClient):
        self._client = status_client

    async def get_status_view(self, char_id: int, tab_key: str, state_data: dict[str, Any], bot: Bot) -> StatusViewDTO:
        """
        Основной метод получения любой вкладки статуса (Био, Скиллы, Моды).
        """
        log.info(f"StatusOrchestrator | action=get_view char_id={char_id} tab={tab_key}")

        # session_context = state_data.get(FSM_CONTEXT_KEY, {})
        # session_dto = SessionDataDTO(**session_context)
        # anim_service = UIAnimationService(bot=bot, message_data=session_dto)

        async def run_logic():
            data = await self._client.get_full_data(char_id)
            if not data:
                return None

            text, kb = None, None

            if tab_key == "bio":
                ui_bio = CharacterMenuUIService(
                    callback_data=StatusNavCallback(key=tab_key, char_id=char_id), state_data=state_data
                )
                text, kb = await ui_bio.render_bio_menu(data)
            elif tab_key == "skills":
                ui_skill = CharacterSkillStatusService(
                    callback_data=StatusNavCallback(key=tab_key, char_id=char_id), state_data=state_data
                )
                text, kb = await ui_skill.render_skill_menu(data)
            elif tab_key == "modifiers":
                ui_mod = CharacterModifierUIService(
                    callback_data=StatusNavCallback(key=tab_key, char_id=char_id), state_data=state_data
                )
                text, kb = await ui_mod.render_modifier_menu(data)
            else:
                return None

            if text and kb:
                return StatusViewDTO(content=ViewResultDTO(text=text, kb=kb), char_id=char_id, current_tab=tab_key)
            return None

        # results = await asyncio.gather(
        #     anim_service.animate_loading(duration=0.5, text="..."),
        #     run_logic(),
        # )
        # return results[1] or StatusViewDTO()

        result = await run_logic()
        return result or StatusViewDTO()

    async def get_skill_view(
        self, char_id: int, level: str, key: str, state_data: dict[str, Any], bot: Bot
    ) -> StatusViewDTO:
        """Получение вложенных меню навыков."""
        log.info(f"StatusOrchestrator | action=get_skill_view char_id={char_id} level={level} key={key}")

        # session_context = state_data.get(FSM_CONTEXT_KEY, {})
        # session_dto = SessionDataDTO(**session_context)
        # anim_service = UIAnimationService(bot=bot, message_data=session_dto)

        async def run_logic():
            data = await self._client.get_full_data(char_id)
            if not data:
                return None

            ui = CharacterSkillStatusService(
                callback_data=StatusSkillsCallback(key=key, char_id=char_id, level=level), state_data=state_data
            )
            text, kb = await ui.render_skill_menu(data)

            if text and kb:
                return StatusViewDTO(content=ViewResultDTO(text=text, kb=kb), char_id=char_id, current_tab="skills")
            return None

        # results = await asyncio.gather(
        #     anim_service.animate_loading(duration=0.5, text="..."),
        #     run_logic(),
        # )
        # return results[1] or StatusViewDTO()

        result = await run_logic()
        return result or StatusViewDTO()

    async def change_skill_mode(self, char_id: int, skill_key: str, new_mode: str) -> bool:
        """Изменяет режим прокачки навыка."""
        return await self._client.update_skill_state(char_id, skill_key, new_mode)

    async def get_modifier_view(
        self, char_id: int, level: str, key: str, state_data: dict[str, Any], bot: Bot
    ) -> StatusViewDTO:
        """Получение вложенных меню модификаторов."""
        log.info(f"StatusOrchestrator | action=get_modifier_view char_id={char_id} level={level} key={key}")

        # session_context = state_data.get(FSM_CONTEXT_KEY, {})
        # session_dto = SessionDataDTO(**session_context)
        # anim_service = UIAnimationService(bot=bot, message_data=session_dto)

        async def run_logic():
            data = await self._client.get_full_data(char_id)
            if not data:
                return None

            ui = CharacterModifierUIService(
                callback_data=StatusModifierCallback(key=key, char_id=char_id, level=level), state_data=state_data
            )
            text, kb = await ui.render_modifier_menu(data)

            if text and kb:
                return StatusViewDTO(content=ViewResultDTO(text=text, kb=kb), char_id=char_id, current_tab="modifiers")
            return None

        # results = await asyncio.gather(
        #     anim_service.animate_loading(duration=0.5, text="..."),
        #     run_logic(),
        # )
        # return results[1] or StatusViewDTO()

        result = await run_logic()
        return result or StatusViewDTO()

    def get_content_coords(self, state_data: dict, user_id: int | None = None) -> MessageCoordsDTO | None:
        """Возвращает координаты сообщения из FSM."""
        session_context = state_data.get(FSM_CONTEXT_KEY, {})
        content = session_context.get("message_content", {})
        if content:
            return MessageCoordsDTO(chat_id=content["chat_id"], message_id=content["message_id"])
        return None
