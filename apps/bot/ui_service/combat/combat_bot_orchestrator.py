import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import User

from apps.bot.core_client.combat_rbc_client import CombatRBCClient
from apps.bot.resources.keyboards.combat_callback import (
    CombatControlCallback,
    CombatFlowCallback,
    CombatMenuCallback,
)
from apps.bot.resources.texts.error_messages import ErrorKeys
from apps.bot.ui_service.base_bot_orchestrator import BaseBotOrchestrator
from apps.bot.ui_service.combat.helpers.combat_state_manager import CombatStateManager
from apps.bot.ui_service.combat.services.content_ui import CombatContentUI
from apps.bot.ui_service.combat.services.flow_ui import CombatFlowUI
from apps.bot.ui_service.combat.services.menu_ui import CombatMenuUI
from apps.bot.ui_service.dto.view_dto import UnifiedViewDTO
from apps.bot.ui_service.error.error_bot_orchestrator import ErrorBotOrchestrator
from apps.common.schemas_dto.game_state_enum import GameState


class CombatBotOrchestrator(BaseBotOrchestrator):
    """
    Оркестратор боевой системы (RBC).
    Управляет локальным стейтом (FSM) и синхронизирует два сообщения (Menu/Content).
    """

    def __init__(self, client: CombatRBCClient):
        super().__init__(expected_state=GameState.COMBAT)
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
        task_snapshot = self.client.get_snapshot(char_id)
        task_logs = self.client.get_data(char_id, "logs", {"page": 0})

        snapshot_res, logs_res = await asyncio.gather(task_snapshot, task_logs)

        # Проверка смены стейта
        switch_result = await self.check_and_switch_state(snapshot_res)
        if switch_result:
            return switch_result

        if not snapshot_res.payload or not logs_res.payload:
            raise ValueError("Incomplete data from backend")

        snapshot = snapshot_res.payload

        # Проверка статуса для правильного рендера
        if snapshot.status == "waiting":
            content_view = await self.flow_ui.render_waiting_screen(snapshot)
        elif snapshot.player.is_dead and snapshot.status == "active":
            content_view = await self.flow_ui.render_spectator_mode(snapshot)
        else:
            content_view = await self.content_ui.render_content("main", snapshot, {})

        menu_view = await self.menu_ui.render_menu("log", logs_res.payload)

        return UnifiedViewDTO(content=content_view, menu=menu_view)

    # --- Handlers ---

    async def handle_menu_event(self, user: User, callback_data: CombatMenuCallback) -> UnifiedViewDTO:
        """
        Обработка действий с верхним сообщением (Лог, Статус, Настройки).
        Вход: CombatMenuCallback (page, refresh, info, settings).
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return self.error_orchestrator.view_session_expired(user.id, "CombatMenu")

        # 1. LOG PAGINATION / REFRESH
        if callback_data.action == "page" or callback_data.action == "refresh":
            page = int(callback_data.value) if callback_data.value else 0

            # Запрашиваем логи
            task_logs = self.client.get_data(char_id, "logs", {"page": page})

            # Если это Refresh, то обновляем и Дашборд тоже
            task_snapshot = None
            if callback_data.action == "refresh":
                task_snapshot = self.client.get_snapshot(char_id)

            if task_snapshot:
                snapshot_res, logs_res = await asyncio.gather(task_snapshot, task_logs)

                switch_result = await self.check_and_switch_state(snapshot_res)
                if switch_result:
                    return switch_result

                if not snapshot_res.payload or not logs_res.payload:
                    raise ValueError("Incomplete data")

                snapshot = snapshot_res.payload

                # Рендерим оба с учетом статуса
                if snapshot.status == "waiting":
                    content_view = await self.flow_ui.render_waiting_screen(snapshot)
                elif snapshot.player.is_dead and snapshot.status == "active":
                    content_view = await self.flow_ui.render_spectator_mode(snapshot)
                else:
                    manager = CombatStateManager(self.director.state)
                    draft = await manager.get_payload()
                    content_view = await self.content_ui.render_content("main", snapshot, draft)

                menu_view = await self.menu_ui.render_menu("log", logs_res.payload)
                return UnifiedViewDTO(content=content_view, menu=menu_view)
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
            response = await self.client.get_data(char_id, "info", {"target_id": target_id})

            menu_view = await self.menu_ui.render_menu("info", response.payload)
            return UnifiedViewDTO(menu=menu_view)

        # 3. SETTINGS (Toggle Grid / Auto)
        elif callback_data.action == "settings":
            pass

        return UnifiedViewDTO()

    async def handle_control_event(
        self, user: User, callback_data: CombatControlCallback, manager: CombatStateManager
    ) -> UnifiedViewDTO:
        """
        Единая точка входа для событий 'c_ctrl' (Нижнее сообщение).
        Маршрутизирует действие в зависимости от action.
        """

        # 1. CLICKS ON GRID (Зоны атаки/защиты)
        if callback_data.action == "zone":
            return await self._handle_zone_click(user, callback_data, manager)

        # 2. NAVIGATION (Смена вкладок клавиатуры)
        elif callback_data.action == "nav":
            return await self._handle_navigation(user, callback_data, manager)

        # 3. PICKING ITEMS/SKILLS (Выбор внутри вкладки)
        elif callback_data.action == "pick":
            return await self._handle_entity_pick(user, callback_data, manager)

        # 4. FALLBACK / ERROR
        return self.error_orchestrator.create_error_view(
            error_key=ErrorKeys.UNKNOWN_ERROR, user_id=user.id, source=f"combat_control:{callback_data.action}"
        )

    async def handle_flow_event(self, user: User, callback_data: CombatFlowCallback) -> tuple[UnifiedViewDTO, bool]:
        """
        Обработка глобальных действий (Submit, Leave).
        Возвращает (UnifiedViewDTO, is_waiting).
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return self.error_orchestrator.view_session_expired(user.id, "CombatFlow"), False

        if callback_data.action == "submit":
            # 1. Сбор данных из FSM (Draft)
            manager = CombatStateManager(self.director.state)
            move_data = await manager.get_move_data()

            # 2. Отправка хода
            response = await self.client.register_move(char_id, 0, move_data)

            # 3. Проверка смены стейта
            switch_result = await self.check_and_switch_state(response)
            if switch_result:
                return switch_result, False

            if not response.payload:
                raise ValueError("No snapshot data")

            snapshot = response.payload

            # Очистка драфта после успешного хода
            await manager.clear_draft()

            # Если статус waiting -> возвращаем Waiting View и флаг True
            if snapshot.status == "waiting":
                view = await self.flow_ui.render_waiting_screen(snapshot)
                return UnifiedViewDTO(content=view), True
            else:
                # Если статус active -> показываем новый ход и флаг False
                # Проверка на смерть
                if snapshot.player.is_dead:
                    content_view = await self.flow_ui.render_spectator_mode(snapshot)
                else:
                    content_view = await self.content_ui.render_content("main", snapshot, {})
                return UnifiedViewDTO(content=content_view), False

        elif callback_data.action == "leave":
            # Выход из боя (сдаться или просто выйти, если бой окончен)
            # Пока просто переключаем стейт на LOBBY (заглушка)
            return await self.director.set_scene(GameState.LOBBY, None), False

        return UnifiedViewDTO(), False

    async def check_combat_status(self) -> tuple[UnifiedViewDTO, bool]:
        """
        Метод для поллинга.
        Возвращает (UnifiedViewDTO, is_waiting).
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return UnifiedViewDTO(), False  # Error

        # Запрашиваем снапшот и логи
        task_snapshot = self.client.get_snapshot(char_id)
        task_logs = self.client.get_data(char_id, "logs", {"page": 0})

        snapshot_res, logs_res = await asyncio.gather(task_snapshot, task_logs)

        # Проверка смены стейта
        switch_result = await self.check_and_switch_state(snapshot_res)
        if switch_result:
            return switch_result, False

        if not snapshot_res.payload or not logs_res.payload:
            # Если данных нет, считаем что ждем (или ошибка)
            return UnifiedViewDTO(), True

        snapshot = snapshot_res.payload

        if snapshot.status == "active":
            # Бой активен -> рендерим Main (или Spectator)
            if snapshot.player.is_dead:
                content_view = await self.flow_ui.render_spectator_mode(snapshot)
            else:
                content_view = await self.content_ui.render_content("main", snapshot, {})

            menu_view = await self.menu_ui.render_menu("log", logs_res.payload)
            return UnifiedViewDTO(content=content_view, menu=menu_view), False

        # Waiting -> рендерим Waiting (с обновленным логом)
        content_view = await self.flow_ui.render_waiting_screen(snapshot)
        menu_view = await self.menu_ui.render_menu("log", logs_res.payload)
        return UnifiedViewDTO(content=content_view, menu=menu_view), True

    def get_submit_poller(
        self, user: User, callback: CombatFlowCallback
    ) -> Callable[[], Awaitable[tuple[UnifiedViewDTO, bool]]]:
        """
        Возвращает функцию-поллер для анимации.
        Первый вызов -> Submit.
        Последующие -> Check Status.
        """
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

    async def _handle_zone_click(
        self, user: User, event: CombatControlCallback, manager: CombatStateManager
    ) -> UnifiedViewDTO:
        """
        Обработка клика по зоне.
        Обновляет FSM -> Запрашивает Snapshot/Logs -> Рендерит Main Dashboard.
        """
        # 1. WRITE (Redis): Мгновенная фиксация выбора (Draft)
        await manager.toggle_zone(layer=event.layer, zone_id=event.value)

        # Подготовка данных
        char_id = await self.director.get_char_id()
        if not char_id:
            return self.error_orchestrator.view_session_expired(user.id, "CombatZone")

        # 2. NETWORK (Parallel Fetch)
        task_snapshot = self.client.get_snapshot(char_id)
        task_logs = self.client.get_data(char_id, "logs", {"page": 0})

        snapshot_res, logs_res = await asyncio.gather(task_snapshot, task_logs)

        # Проверка смены стейта
        switch_result = await self.check_and_switch_state(snapshot_res)
        if switch_result:
            return switch_result

        if not snapshot_res.payload or not logs_res.payload:
            raise ValueError("Incomplete data from backend")

        # 3. UI RENDER
        draft_state = await manager.get_payload()

        snapshot = snapshot_res.payload
        if snapshot.player.is_dead and snapshot.status == "active":
            content_view = await self.flow_ui.render_spectator_mode(snapshot)
        else:
            content_view = await self.content_ui.render_content(screen="main", snapshot=snapshot, selection=draft_state)

        menu_view = await self.menu_ui.render_menu(view_type="log", data=logs_res.payload)

        return UnifiedViewDTO(content=content_view, menu=menu_view)

    async def _handle_navigation(
        self, user: User, event: CombatControlCallback, manager: CombatStateManager
    ) -> UnifiedViewDTO:
        """
        Обработка навигации (Main <-> Skills <-> Items).
        Запрашивает Snapshot/Logs -> Рендерит нужный экран.
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return self.error_orchestrator.view_session_expired(user.id, "CombatNav")

        # 2. NETWORK (Parallel Fetch)
        task_snapshot = self.client.get_snapshot(char_id)
        task_logs = self.client.get_data(char_id, "logs", {"page": 0})

        snapshot_res, logs_res = await asyncio.gather(task_snapshot, task_logs)

        switch_result = await self.check_and_switch_state(snapshot_res)
        if switch_result:
            return switch_result

        if not snapshot_res.payload or not logs_res.payload:
            raise ValueError("Incomplete data from backend")

        # 3. UI RENDER
        draft_state = await manager.get_payload()

        content_view = await self.content_ui.render_content(
            screen=event.value, snapshot=snapshot_res.payload, selection=draft_state
        )

        menu_view = await self.menu_ui.render_menu(view_type="log", data=logs_res.payload)

        return UnifiedViewDTO(content=content_view, menu=menu_view)

    async def _handle_entity_pick(
        self, user: User, event: CombatControlCallback, manager: CombatStateManager
    ) -> UnifiedViewDTO:
        """
        Обработка выбора скилла или предмета.
        Skill -> FSM -> Main.
        Item -> Instant Action -> Main.
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return self.error_orchestrator.view_session_expired(user.id, "CombatPick")

        if event.layer == "abil":
            # Выбор скилла (Draft)
            await manager.set_ability(event.value)

            # Запрашиваем данные для возврата на главную
            task_snapshot = self.client.get_snapshot(char_id)
            task_logs = self.client.get_data(char_id, "logs", {"page": 0})

            snapshot_res, logs_res = await asyncio.gather(task_snapshot, task_logs)

            switch_result = await self.check_and_switch_state(snapshot_res)
            if switch_result:
                return switch_result

            if not snapshot_res.payload or not logs_res.payload:
                raise ValueError("Incomplete data")

            # Рендер Main
            draft_state = await manager.get_payload()
            content_view = await self.content_ui.render_content("main", snapshot_res.payload, draft_state)
            menu_view = await self.menu_ui.render_menu("log", logs_res.payload)

            return UnifiedViewDTO(content=content_view, menu=menu_view)

        elif event.layer == "item":
            # Используем предмет (Instant Action)
            item_id = int(event.value)
            response = await self.client.perform_action(char_id, "use_item", {"item_id": item_id})

            if not response.payload:
                raise ValueError("No action result")

            # Запрашиваем логи
            task_logs = self.client.get_data(char_id, "logs", {"page": 0})
            logs_res = await task_logs

            # Рендер Main
            snapshot = response.payload.updated_snapshot
            if not snapshot:
                snap_res = await self.client.get_snapshot(char_id)
                snapshot = snap_res.payload

            if not snapshot:
                raise ValueError("No snapshot")

            draft_state = await manager.get_payload()
            content_view = await self.content_ui.render_content("main", snapshot, draft_state)
            menu_view = await self.menu_ui.render_menu("log", logs_res.payload)

            return UnifiedViewDTO(content=content_view, menu=menu_view)

        return UnifiedViewDTO()
