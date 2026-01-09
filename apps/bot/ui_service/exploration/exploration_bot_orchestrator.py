from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.core_client.combat_rbc_client import CombatRBCClient
from apps.bot.core_client.exploration import ExplorationClient
from apps.bot.resources.keyboards.callback_data import EncounterCallback
from apps.bot.ui_service.exploration.dto.exploration_view_dto import ExplorationViewDTO
from apps.bot.ui_service.exploration.exploration_ui import ExplorationUIService
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import MessageCoordsDTO, ViewResultDTO
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.schemas_dto.exploration_dto import DetectionStatus, EncounterDTO, WorldNavigationDTO


class ExplorationBotOrchestrator:
    """
    Оркестратор навигации и исследования мира.
    """

    def __init__(self, exploration_client: ExplorationClient, combat_client: CombatRBCClient):
        self._expl_client = exploration_client
        self._combat_client = combat_client

    def _get_ui(self, state_data: dict) -> ExplorationUIService:
        """Внутренняя фабрика для UI сервиса."""
        session_context = state_data.get(FSM_CONTEXT_KEY, {})
        char_id = session_context.get("char_id")

        if not char_id:
            char_id = state_data.get("char_id")

        return ExplorationUIService(state_data=state_data, char_id=char_id)

    # --- Обертки для доступа к координатам сообщений через UI ---
    def get_content_coords(self, state_data: dict) -> MessageCoordsDTO | None:
        """Возвращает (chat_id, message_id) для основного контента."""
        data = self._get_ui(state_data).get_message_content_data()
        return MessageCoordsDTO(chat_id=data[0], message_id=data[1]) if data else None

    # -----------------------------------------------------------

    async def handle_move(self, char_id: int, target_loc_id: str, state_data: dict) -> ExplorationViewDTO:
        """
        Обрабатывает перемещение персонажа.
        """
        ui = self._get_ui(state_data)
        result = await self._expl_client.move(char_id, target_loc_id)

        if isinstance(result, EncounterDTO):
            # Автоматический вход в бой при засаде
            if result.status == DetectionStatus.AMBUSH:
                # try:
                # enemy_id = int(result.encounter_id)
                # snapshot = await self._combat_client.start_battle(players=[char_id], enemies=[enemy_id])
                # return ExplorationViewDTO(
                #     new_state="InGame.combats",
                #     combat_session_id=snapshot.session_id,
                #     combat_target_id=snapshot.current_target.char_id if snapshot.current_target else None,
                #     alert_text="⚔️ ВАС АТАКОВАЛИ!",
                # )
                pass  # TODO: Fix start_battle call
                # except ValueError:
                #     pass  # Если ID не число, показываем как обычную встречу

            view = ui.render_encounter(result)
            return ExplorationViewDTO(content=view, encounter_id=result.encounter_id)

        if isinstance(result, WorldNavigationDTO):
            view = ui.render_navigation(result)
            return ExplorationViewDTO(content=view)

        # Если перемещение не удалось
        return ExplorationViewDTO(content=ViewResultDTO(text="🚫 <b>Путь заблокирован</b> или локация недоступна."))

    async def get_current_view(self, char_id: int, state_data: dict) -> ExplorationViewDTO:
        """
        Возвращает вид текущей локации (без перемещения).
        """
        ui = self._get_ui(state_data)
        dto = await self._expl_client.get_current_location(char_id)

        if not dto:
            return ExplorationViewDTO(content=ViewResultDTO(text="Ошибка загрузки локации."))

        view = ui.render_navigation(dto)
        return ExplorationViewDTO(content=view)

    async def resolve_encounter(
        self, action: str, target_id: str, char_id: int, state_data: dict
    ) -> ExplorationViewDTO:
        """
        Обрабатывает действия во время встречи (attack, bypass, inspect).
        """
        # ui = self._get_ui(state_data) # Удалено: не используется

        if action == "attack":
            try:
                # enemy_id = int(target_id)
                # snapshot = await self._combat_client.start_battle(players=[char_id], enemies=[enemy_id])

                # return ExplorationViewDTO(
                #     new_state="InGame.combats",
                #     combat_session_id=snapshot.session_id,
                #     combat_target_id=snapshot.current_target.char_id if snapshot.current_target else None,
                #     alert_text="⚔️ Бой начинается!",
                # )
                return ExplorationViewDTO(content=ViewResultDTO(text="Ошибка: Бой временно недоступен (Refactoring)"))

            except (ValueError, TypeError):
                return ExplorationViewDTO(content=ViewResultDTO(text="Ошибка ID цели"))

        elif action == "bypass":
            # Возврат к карте
            result = await self.get_current_view(char_id, state_data)
            result.alert_text = "Вы успешно обошли угрозу."
            return result

        elif action == "inspect":
            # Заглушка для осмотра
            kb = InlineKeyboardBuilder()
            kb.button(text="🔙 Назад", callback_data=EncounterCallback(action="bypass", target_id=target_id).pack())

            return ExplorationViewDTO(
                content=ViewResultDTO(
                    text="🔍 <b>Осмотр:</b>\n\nЭто очень интересный объект. Вы видите...", kb=kb.as_markup()
                ),
                alert_text="Осмотр...",
            )

        return ExplorationViewDTO(content=ViewResultDTO(text="Неизвестное действие."))
