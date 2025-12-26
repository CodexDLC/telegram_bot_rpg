from aiogram.fsm.context import FSMContext
from loguru import logger as log

from apps.bot.core_client.scenario_client import ScenarioClient
from apps.bot.resources.keyboards.callback_data import ScenarioCallback
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import MessageCoordsDTO, ViewResultDTO
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.scenario.dto.scenario_view_dto import ScenarioViewDTO
from apps.bot.ui_service.scenario.scenario_ui_service import ScenarioUIService
from apps.common.services.core_service.manager.account_manager import AccountManager


class ScenarioBotOrchestrator:
    """
    Оркестратор UI для системы сценариев.
    Координирует получение данных от Core и их отрисовку через UI-сервис.
    """

    def __init__(self, client: ScenarioClient, account_manager: AccountManager):
        self._client = client
        self._account_manager = account_manager

    def get_content_coords(self, state_data: dict) -> MessageCoordsDTO | None:
        """Возвращает координаты сообщения из FSM."""
        session_context = state_data.get(FSM_CONTEXT_KEY, {})
        if isinstance(session_context, dict):
            message_content = session_context.get("message_content")
            if isinstance(message_content, dict):
                chat_id = message_content.get("chat_id")
                message_id = message_content.get("message_id")
                if chat_id and message_id:
                    return MessageCoordsDTO(chat_id=chat_id, message_id=message_id)
        return None

    async def initialize_view(
        self, char_id: int, callback_data: ScenarioCallback, state: FSMContext
    ) -> ScenarioViewDTO:
        """
        Запускает сценарий и возвращает его первую сцену.
        """
        log.info(
            f"ScenarioBotOrchestrator | action=initialize_view char_id={char_id} quest='{callback_data.quest_key}'"
        )

        # 1. Получаем "обратный адрес"
        prev_state = await state.get_state()
        account_data = await self._account_manager.get_account_data(char_id)

        prev_loc = "unknown"
        if account_data:
            prev_loc = str(account_data.get("location_id", "unknown"))

        # 2. Вызываем Core-оркестратор
        response_dto = await self._client.initialize_scenario(
            char_id, str(callback_data.quest_key), str(prev_state), prev_loc
        )

        if response_dto.status != "success":
            error_content = ViewResultDTO(text=f"Ошибка запуска сценария: {response_dto.payload}")
            return ScenarioViewDTO(content=error_content, is_terminal=True)

        # 3. Рендерим сцену
        ui_service = ScenarioUIService()
        view_result = ui_service.render_scene(response_dto.payload)

        return ScenarioViewDTO(
            content=view_result,
            is_terminal=response_dto.payload.is_terminal,
            node_key=response_dto.payload.node_key,
            extra_data=response_dto.payload.extra_data,
        )

    async def step_view(self, char_id: int, action_id: str) -> ScenarioViewDTO:
        """
        Обрабатывает выбор игрока и возвращает следующую сцену.
        """
        log.info(f"ScenarioBotOrchestrator | action=step_view char_id={char_id} action_id='{action_id}'")

        response_dto = await self._client.step_scenario(char_id, action_id)

        if response_dto.status != "success":
            error_content = ViewResultDTO(text=f"Ошибка шага в сценарии: {response_dto.payload}")
            return ScenarioViewDTO(content=error_content, is_terminal=True)

        ui_service = ScenarioUIService()
        view_result = ui_service.render_scene(response_dto.payload)

        return ScenarioViewDTO(
            content=view_result,
            is_terminal=response_dto.payload.is_terminal,
            node_key=response_dto.payload.node_key,
            extra_data=response_dto.payload.extra_data,
        )

    async def finalize_view(self, char_id: int) -> dict:
        """
        Завершает сценарий и возвращает данные для возврата в мир.
        """
        log.info(f"ScenarioBotOrchestrator | action=finalize_view char_id={char_id}")

        response_dict = await self._client.finalize_scenario(char_id)

        return response_dict
