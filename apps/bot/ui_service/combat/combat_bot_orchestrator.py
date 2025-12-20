# apps/bot/ui_service/combat/combat_bot_orchestrator.py
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.core_client.combat_rbc_client import CombatRBCClient
from apps.bot.core_client.exploration import ExplorationClient
from apps.bot.ui_service.combat.combat_ui_service import CombatUIService
from apps.bot.ui_service.combat.dto.combat_view_dto import CombatViewDTO
from apps.bot.ui_service.exploration.exploration_ui import ExplorationUIService
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.hub_entry_service import HubEntryService
from apps.bot.ui_service.menu_service import MenuService
from apps.bot.ui_service.ui_common_dto import MessageCoordsDTO, ViewResultDTO
from apps.common.schemas_dto.combat_source_dto import CombatDashboardDTO, CombatMoveDTO
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.arena_manager import ArenaManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.common.services.core_service.manager.world_manager import WorldManager


class CombatBotOrchestrator:
    def __init__(
        self,
        client: CombatRBCClient,
        account_manager: AccountManager,
        exploration_client: ExplorationClient,
        arena_manager: ArenaManager,
        combat_manager: CombatManager,
        world_manager: WorldManager,
    ):
        self.client = client
        self.account_manager = account_manager
        self.exploration_client = exploration_client
        self.arena_manager = arena_manager
        self.combat_manager = combat_manager
        self.world_manager = world_manager

    def _get_ui(self, state_data: dict) -> CombatUIService:
        """Внутренняя фабрика для UI сервиса."""
        char_id = state_data.get("char_id")
        if not char_id:
            context = state_data.get("fsm_context_key", {})
            if isinstance(context, dict):
                char_id = context.get("char_id")

        if not char_id:
            char_id = state_data.get("combat_char_id")

        return CombatUIService(state_data=state_data, char_id=char_id)  # type: ignore

    # --- Обертки для доступа к координатам сообщений через UI ---
    def get_content_coords(self, state_data: dict) -> MessageCoordsDTO | None:
        """Возвращает (chat_id, message_id) для основного контента (Дашборд)."""
        data = self._get_ui(state_data).get_message_content_data()
        return MessageCoordsDTO(chat_id=data[0], message_id=data[1]) if data else None

    def get_menu_coords(self, state_data: dict) -> MessageCoordsDTO | None:
        """Возвращает (chat_id, message_id) для меню (Лог боя/Кнопки)."""
        data = self._get_ui(state_data).get_message_menu_data()
        return MessageCoordsDTO(chat_id=data[0], message_id=data[1]) if data else None

    # -----------------------------------------------------------

    async def leave_combat(self, char_id: int, state_data: dict, session: AsyncSession) -> CombatViewDTO:
        """Логика выхода из боя: очистка и подготовка UI для возврата."""
        session_context = state_data.get(FSM_CONTEXT_KEY, {})
        prev_state_str = session_context.get("previous_state", "InGame:navigation")

        result = CombatViewDTO()

        if prev_state_str == "ArenaState:menu":
            result.new_state = "ArenaState:menu"
            hub = HubEntryService(
                char_id=char_id,
                target_loc="svc_arena_main",
                state_data=state_data,
                session=session,
                account_manager=self.account_manager,
                arena_manager=self.arena_manager,
                combat_manager=self.combat_manager,
            )
            text, kb, _ = await hub.render_hub_menu()
            result.content = ViewResultDTO(text=text, kb=kb)
        else:
            result.new_state = "InGame:navigation"
            # Получаем текущую локацию через клиент
            loc_dto = await self.exploration_client.get_current_location(char_id)

            if loc_dto:
                expl_ui = ExplorationUIService(state_data=state_data, char_id=char_id)
                result.content = expl_ui.render_navigation(loc_dto)
            else:
                result.content = ViewResultDTO(text="Ошибка загрузки локации.")

        menu_service = MenuService(
            game_stage="in_game", state_data=state_data, session=session, account_manager=self.account_manager
        )
        m_text, m_kb = await menu_service.get_data_menu()
        result.menu = ViewResultDTO(text=m_text, kb=m_kb)

        return result

    async def use_item(self, session_id: str, char_id: int, item_id: int, state_data: dict) -> CombatViewDTO:
        """Использование предмета в бою."""
        success, msg = await self.client.use_consumable(session_id, char_id, item_id)

        ui = self._get_ui(state_data)
        snapshot = await self.client.get_snapshot(session_id, char_id)

        menu_view = await ui.render_items_menu(snapshot)

        return CombatViewDTO(menu=menu_view)

    async def toggle_zone(
        self, session_id: str, char_id: int, layer: str, zone_id: str, state_data: dict
    ) -> CombatViewDTO:
        """Переключение зоны атаки/защиты."""
        selection: dict[str, list[str]] = state_data.get("combat_selection", {"atk": [], "def": []})
        import copy

        new_selection = copy.deepcopy(selection)

        current_list = new_selection.get(layer, [])

        if zone_id in current_list:
            current_list.remove(zone_id)
        else:
            current_list.clear()
            current_list.append(zone_id)

        new_selection[layer] = current_list

        ui = self._get_ui(state_data)
        snapshot = await self.client.get_snapshot(session_id, char_id)
        content_view = await self._render_by_status(snapshot, new_selection, ui)

        return CombatViewDTO(content=content_view, fsm_update={"combat_selection": new_selection})

    async def select_ability(self, session_id: str, char_id: int, ability_id: str, state_data: dict) -> CombatViewDTO:
        """Выбор способности."""
        ui = self._get_ui(state_data)
        snapshot = await self.client.get_snapshot(session_id, char_id)
        menu_view = await ui.render_skills_menu(snapshot)

        return CombatViewDTO(menu=menu_view, fsm_update={"combat_selected_ability": ability_id})

    async def get_dashboard_view(
        self, session_id: str, char_id: int, selection: dict, state_data: dict
    ) -> CombatViewDTO:
        """
        Точка входа для Refresh и первого отображения.
        """
        ui = self._get_ui(state_data)
        snapshot = await self.client.get_snapshot(session_id, char_id)

        content_view = await self._render_by_status(snapshot, selection, ui)
        log_view = await ui.render_combat_log(snapshot, page=0)

        target_id = snapshot.current_target.char_id if snapshot.current_target else None

        return CombatViewDTO(target_id=target_id, content=content_view, menu=log_view)

    async def handle_submit(
        self, session_id: str, char_id: int, move: CombatMoveDTO, state_data: dict
    ) -> CombatViewDTO:
        """
        Логика подтверждения хода.
        """
        ui = self._get_ui(state_data)
        await self.client.register_move(session_id, char_id, move.target_id, move.model_dump())
        snapshot = await self.client.get_snapshot(session_id, char_id)

        content_view = await self._render_by_status(snapshot, {}, ui)
        log_view = await ui.render_combat_log(snapshot, page=0)

        target_id = snapshot.current_target.char_id if snapshot.current_target else None

        return CombatViewDTO(target_id=target_id, content=content_view, menu=log_view)

    async def check_combat_status(self, session_id: str, char_id: int, state_data: dict) -> CombatViewDTO | None:
        """
        Метод для поллинга.
        """
        snapshot = await self.client.get_snapshot(session_id, char_id)

        if snapshot.status == "waiting":
            return None

        ui = self._get_ui(state_data)
        content_view = await self._render_by_status(snapshot, {}, ui)
        log_view = await ui.render_combat_log(snapshot, page=0)

        target_id = snapshot.current_target.char_id if snapshot.current_target else None

        return CombatViewDTO(target_id=target_id, content=content_view, menu=log_view)

    async def get_menu_view(self, session_id: str, char_id: int, menu_type: str, state_data: dict) -> ViewResultDTO:
        """Отрисовка подменю (скиллы/вещи)."""
        ui = self._get_ui(state_data)
        snapshot = await self.client.get_snapshot(session_id, char_id)
        if menu_type == "skills":
            return await ui.render_skills_menu(snapshot)
        else:
            return await ui.render_items_menu(snapshot)

    async def get_log_view(self, session_id: str, char_id: int, page: int, state_data: dict) -> ViewResultDTO:
        """Отрисовка лога боя."""
        ui = self._get_ui(state_data)
        snapshot = await self.client.get_snapshot(session_id, char_id)
        return await ui.render_combat_log(snapshot, page)

    async def start_new_battle(
        self, players: list[int], enemies: list[int], state_data: dict
    ) -> tuple[str, int | None, str, InlineKeyboardMarkup]:
        """Начинает новый бой и возвращает начальный дашборд."""
        ui = self._get_ui(state_data)
        snapshot = await self.client.start_battle(players, enemies)

        view = await self._render_by_status(snapshot, {}, ui)

        target_id = snapshot.current_target.char_id if snapshot.current_target else None
        # Здесь возвращаем кортеж, так как это фабричный метод
        return snapshot.session_id, target_id, view.text, view.kb

    async def _render_by_status(
        self, snapshot: CombatDashboardDTO, selection: dict, ui: CombatUIService
    ) -> ViewResultDTO:
        """
        Внутренний 'решала'. Возвращает DTO.
        """
        if snapshot.status == "finished":
            return await ui.render_results(snapshot)
        elif snapshot.player.hp_current <= 0:
            return await ui.render_spectator_mode(snapshot)
        elif snapshot.status == "waiting":
            return await ui.render_waiting_screen(snapshot)
        else:
            return await ui.render_dashboard(snapshot, selection)
