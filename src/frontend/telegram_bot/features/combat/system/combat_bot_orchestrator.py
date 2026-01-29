import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import User

from src.frontend.telegram_bot.base.base_orchestrator import BaseBotOrchestrator
from src.frontend.telegram_bot.base.view_dto import UnifiedViewDTO
from src.frontend.telegram_bot.features.combat.client import CombatClient
from src.frontend.telegram_bot.features.combat.resources.keyboards.combat_callback import (
    CombatControlCallback,
    CombatFlowCallback,
    CombatMenuCallback,
)
from src.frontend.telegram_bot.features.combat.system.combat_state_manager import CombatStateManager
from src.frontend.telegram_bot.features.combat.system.components.content_ui import CombatContentUI
from src.frontend.telegram_bot.features.combat.system.components.flow_ui import CombatFlowUI
from src.frontend.telegram_bot.features.combat.system.components.menu_ui import CombatMenuUI
from src.frontend.telegram_bot.services.error.logic.orchestrator import ErrorBotOrchestrator
from src.frontend.telegram_bot.services.error.ui.texts import ErrorKeys
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.combat import CombatDashboardDTO, CombatLogDTO


class CombatBotOrchestrator(BaseBotOrchestrator):
    """
    Оркестратор боевой системы (RBC).
    Управляет локальным стейтом (FSM) и синхронизирует два сообщения (Menu/Content).
    """

    def __init__(self, client: CombatClient):
        super().__init__(expected_state=CoreDomain.COMBAT)
        self.client = client
        self.error_orchestrator = ErrorBotOrchestrator()

        # UI Services (Stateless)
        self.content_ui = CombatContentUI()
        self.menu_ui = CombatMenuUI()
        self.flow_ui = CombatFlowUI()

    # --- Entry Point ---

    async def render(self, payload: Any) -> UnifiedViewDTO:
        """
        Рендер при входе в бой (вызывается Директором).
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return self.error_orchestrator.view_session_expired(0, "CombatRender")

        # Запрашиваем начальное состояние И логи параллельно
        task_snapshot = self.client.get_view(char_id, "snapshot")
        task_logs = self.client.get_view(char_id, "logs", {"page": 0})

        snapshot_res, logs_res = await asyncio.gather(task_snapshot, task_logs)

        # Проверка смены стейта
        switch_result = await self.check_and_switch_state(snapshot_res)
        if switch_result:
            return switch_result

        if not snapshot_res.payload or not logs_res.payload:
            raise ValueError("Incomplete data from backend")

        return await self._compile_view(snapshot_res.payload, logs_res.payload)

    # --- Handlers ---

    async def handle_menu_event(self, user: User, callback_data: CombatMenuCallback) -> UnifiedViewDTO:
        """
        Обработка действий с верхним сообщением (Лог, Статус, Настройки).
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return self.error_orchestrator.view_session_expired(user.id, "CombatMenu")

        # 1. LOG PAGINATION / REFRESH
        if callback_data.action == "page" or callback_data.action == "refresh":
            page = int(callback_data.value) if callback_data.value else 0

            # Запрашиваем логи
            task_logs = self.client.get_view(char_id, "logs", {"page": page})

            # Если это Refresh, то обновляем и Дашборд тоже
            task_snapshot = None
            if callback_data.action == "refresh":
                task_snapshot = self.client.get_view(char_id, "snapshot")

            if task_snapshot:
                snapshot_res, logs_res = await asyncio.gather(task_snapshot, task_logs)

                switch_result = await self.check_and_switch_state(snapshot_res)
                if switch_result:
                    return switch_result

                if not snapshot_res.payload or not logs_res.payload:
                    raise ValueError("Incomplete data")

                # Если есть драфт, подтягиваем его (для сохранения выбора финта при рефрене)
                manager = CombatStateManager(self.director.state)
                draft = await manager.get_payload()

                return await self._compile_view(snapshot_res.payload, logs_res.payload, draft)
            else:
                # Только логи (пагинация)
                response = await task_logs
                if not response.payload:
                    raise ValueError("No logs data")
                menu_view = await self.menu_ui.render_menu("log", response.payload)
                return UnifiedViewDTO(menu=menu_view)

        # 2. INFO (Target Info)
        elif callback_data.action == "info":
            target_id = callback_data.value
            response = await self.client.get_view(char_id, "info", {"target_id": target_id})

            menu_view = await self.menu_ui.render_menu("info", response.payload)
            return UnifiedViewDTO(menu=menu_view)

        return UnifiedViewDTO()

    async def handle_control_event(
        self, user: User, callback_data: CombatControlCallback, manager: CombatStateManager
    ) -> UnifiedViewDTO:
        """
        Единая точка входа для событий 'c_ctrl' (Нижнее сообщение).
        """

        # 1. CLICKS ON FEINTS
        if callback_data.action == "zone":
            return await self._handle_feint_click(user, callback_data, manager)

        # 2. NAVIGATION
        elif callback_data.action == "nav":
            return await self._handle_navigation(user, callback_data, manager)

        # 3. PICKING ITEMS/SKILLS
        elif callback_data.action == "pick":
            return await self._handle_entity_pick(user, callback_data, manager)

        return self.error_orchestrator.create_error_view(
            error_key=ErrorKeys.UNKNOWN_ERROR, user_id=user.id, source=f"combat_control:{callback_data.action}"
        )

    async def handle_flow_event(self, user: User, callback_data: CombatFlowCallback) -> tuple[UnifiedViewDTO, bool]:
        """
        Обработка глобальных действий (Submit, Leave).
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return self.error_orchestrator.view_session_expired(user.id, "CombatFlow"), False

        if callback_data.action == "submit":
            manager = CombatStateManager(self.director.state)
            move_data = await manager.get_move_data()

            if "target_id" not in move_data:
                snap_res = await self.client.get_view(char_id, "snapshot")
                if snap_res.payload and snap_res.payload.target:
                    move_data["target_id"] = snap_res.payload.target.char_id
                else:
                    return UnifiedViewDTO(), False

            # Параллельный запрос: Ход + Логи
            task_turn = self.client.handle_action(char_id, "attack", move_data)
            task_logs = self.client.get_view(char_id, "logs", {"page": 0})

            response, logs_res = await asyncio.gather(task_turn, task_logs)

            switch_result = await self.check_and_switch_state(response)
            if switch_result:
                return switch_result, False

            if not response.payload:
                raise ValueError("No snapshot data")

            await manager.clear_draft()

            # Используем полученные логи (даже если они "старые", это лучше, чем ничего)
            logs = logs_res.payload or CombatLogDTO(logs=[], total=0, page=0)

            view = await self._compile_view(response.payload, logs)

            # Если статус waiting -> возвращаем True для поллинга
            is_waiting = response.payload.status == "waiting"
            return view, is_waiting

        elif callback_data.action == "leave":
            return await self.director.set_scene(CoreDomain.LOBBY, None), False

        return UnifiedViewDTO(), False

    async def check_combat_status(self) -> tuple[UnifiedViewDTO, bool]:
        """
        Метод для поллинга.
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return UnifiedViewDTO(), False

        task_snapshot = self.client.get_view(char_id, "snapshot")
        task_logs = self.client.get_view(char_id, "logs", {"page": 0})

        snapshot_res, logs_res = await asyncio.gather(task_snapshot, task_logs)

        switch_result = await self.check_and_switch_state(snapshot_res)
        if switch_result:
            return switch_result, False

        if not snapshot_res.payload or not logs_res.payload:
            return UnifiedViewDTO(), True

        view = await self._compile_view(snapshot_res.payload, logs_res.payload)
        is_waiting = snapshot_res.payload.status == "waiting"

        return view, is_waiting

    def get_submit_poller(
        self, user: User, callback: CombatFlowCallback
    ) -> Callable[[], Awaitable[tuple[UnifiedViewDTO, bool]]]:
        is_first_run = True

        async def poller() -> tuple[UnifiedViewDTO, bool]:
            nonlocal is_first_run
            if is_first_run:
                is_first_run = False
                return await self.handle_flow_event(user, callback)
            else:
                return await self.check_combat_status()

        return poller

    # --- Internal Logic ---

    async def _handle_feint_click(
        self, user: User, event: CombatControlCallback, manager: CombatStateManager
    ) -> UnifiedViewDTO:
        await manager.toggle_feint(feint_id=event.value)
        return await self._refresh_view_with_draft(user.id, manager)

    async def _handle_navigation(
        self, user: User, event: CombatControlCallback, manager: CombatStateManager
    ) -> UnifiedViewDTO:
        # event.value = 'skills', 'items', 'main'
        return await self._refresh_view_with_draft(user.id, manager, screen=event.value)

    async def _handle_entity_pick(
        self, user: User, event: CombatControlCallback, manager: CombatStateManager
    ) -> UnifiedViewDTO:
        char_id = await self.director.get_char_id()
        if not char_id:
            return self.error_orchestrator.view_session_expired(user.id, "CombatPick")

        if event.layer == "abil":
            await manager.set_ability(event.value)
            return await self._refresh_view_with_draft(user.id, manager)

        elif event.layer == "item":
            item_id = int(event.value)
            response = await self.client.handle_action(char_id, "use_item", {"item_id": item_id})

            if not response.payload:
                raise ValueError("No action result")

            # После использования предмета обновляем логи и показываем Main
            logs_res = await self.client.get_view(char_id, "logs", {"page": 0})
            logs = logs_res.payload or CombatLogDTO(logs=[], total=0, page=0)

            draft = await manager.get_payload()
            return await self._compile_view(response.payload, logs, draft)

        return UnifiedViewDTO()

    # --- Helpers ---

    async def _refresh_view_with_draft(
        self, user_id: int, manager: CombatStateManager, screen: str = "main"
    ) -> UnifiedViewDTO:
        """
        Helper: Загружает данные и рендерит экран с учетом драфта.
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return self.error_orchestrator.view_session_expired(user_id, "Refresh")

        task_snapshot = self.client.get_view(char_id, "snapshot")
        task_logs = self.client.get_view(char_id, "logs", {"page": 0})

        snapshot_res, logs_res = await asyncio.gather(task_snapshot, task_logs)

        switch_result = await self.check_and_switch_state(snapshot_res)
        if switch_result:
            return switch_result

        if not snapshot_res.payload or not logs_res.payload:
            raise ValueError("Incomplete data")

        draft = await manager.get_payload()
        return await self._compile_view(snapshot_res.payload, logs_res.payload, draft, screen)

    async def _compile_view(
        self, snapshot: CombatDashboardDTO, logs: CombatLogDTO, draft_state: dict | None = None, screen: str = "main"
    ) -> UnifiedViewDTO:
        """
        Единый метод сборки View на основе Snapshot и Logs.
        """
        # 1. Content View (Нижнее сообщение)
        if screen != "main":
            # Специфичные экраны (Skills, Items)
            content_view = await self.content_ui.render_content(screen, snapshot, draft_state or {})
        else:
            # Main Logic
            if snapshot.status == "waiting":
                # Waiting (используем main, форматтер подставит анимацию)
                content_view = await self.content_ui.render_content("main", snapshot, draft_state or {})

            elif snapshot.hero.is_dead and snapshot.status == "active":
                # Spectator
                content_view = await self.flow_ui.render_spectator_mode(snapshot)

            else:
                # Active / Finished
                content_view = await self.content_ui.render_content("main", snapshot, draft_state or {})

        # 2. Menu View (Верхнее сообщение)
        menu_view = await self.menu_ui.render_menu("log", logs)

        return UnifiedViewDTO(content=content_view, menu=menu_view)
