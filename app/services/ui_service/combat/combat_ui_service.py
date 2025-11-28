# app/services/ui_service/combat/combat_ui_service.py
import json
import time
from contextlib import suppress
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from app.resources.keyboards.combat_callback import (
    CombatActionCallback,
    CombatLogCallback,
    CombatZoneCallback,
)
from app.resources.schemas_dto.combat_source_dto import (
    CombatSessionContainerDTO,
    StatSourceData,
)
from app.services.core_service.manager.combat_manager import combat_manager
from app.services.game_service.combat.stats_calculator import StatsCalculator
from app.services.ui_service.base_service import BaseUIService
from app.services.ui_service.helpers_ui.combat_formatters import CombatFormatter


class CombatUIService(BaseUIService):
    """
    Сервис для рендеринга пользовательского интерфейса в бою.
    Отвечает за Лог Боя и Панель Управления (Dashboard).
    """

    def __init__(self, user_id: int, char_id: int, session_id: str, state_data: dict[str, Any]):
        super().__init__(state_data=state_data, char_id=char_id)
        self.user_id = user_id
        self.session_id = session_id
        self.fmt = CombatFormatter
        self.LOG_PAGE_SIZE = 5
        log.debug(f"CombatUIService init: user={user_id}, char={char_id}, sess={session_id}")

    # =========================================================================
    # 1. ЛОГ БОЯ (Верхнее сообщение)
    # =========================================================================

    async def render_combat_log(self, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит лог боя с пагинацией и кнопкой обновления.
        """
        all_logs_json = await combat_manager.get_combat_log_list(self.session_id)
        all_logs = []
        for log_json in all_logs_json:
            with suppress(json.JSONDecodeError):
                all_logs.append(json.loads(log_json))

        text = self.fmt.format_log(all_logs, page, self.LOG_PAGE_SIZE)

        kb = InlineKeyboardBuilder()
        total_items = len(all_logs)
        total_pages = (total_items + self.LOG_PAGE_SIZE - 1) // self.LOG_PAGE_SIZE

        # 1. Кнопки пагинации
        btns = []
        if page < total_pages - 1:
            cb_old = CombatLogCallback(page=page + 1).pack()
            btns.append(InlineKeyboardButton(text="< Ранее", callback_data=cb_old))
        if page > 0:
            cb_new = CombatLogCallback(page=page - 1).pack()
            btns.append(InlineKeyboardButton(text="Позже >", callback_data=cb_new))
        if btns:
            kb.row(*btns)

        # 2. Кнопка обновления (чтобы игроки могли пинговать сервер)
        cb_refresh = CombatActionCallback(action="refresh").pack()
        kb.row(InlineKeyboardButton(text="🔄 Обновить лог", callback_data=cb_refresh))

        return text, kb.as_markup()

    # =========================================================================
    # 2. ПАНЕЛЬ УПРАВЛЕНИЯ
    # =========================================================================

    async def render_dashboard(self, current_selection: dict) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит панель управления.
        1. Проверяет, окончен ли бой -> Result Screen.
        2. Проверяет, мертв ли игрок -> Spectator Mode.
        3. Иначе -> Активный режим боя.
        """
        # 1. ПРОВЕРКА СТАТУСА БОЯ (META)
        meta = await combat_manager.get_session_meta(self.session_id)
        if meta and int(meta.get("active", 1)) == 0:
            return await self._render_results(meta)

        player_dto, enemies_data, allies_data = await self._prepare_dashboard_data()

        # 2. ПРОВЕРКА НА СМЕРТЬ (SPECTATOR MODE)
        if player_dto and player_dto.state and player_dto.state.hp_current <= 0:
            return self._render_spectator_mode(enemies_data, allies_data)

        # 3. АКТИВНЫЙ РЕЖИМ

        # Извлекаем ID текущей цели и заряды
        target_id = None
        charges = 0
        targets_count = 0

        if player_dto and player_dto.state:
            targets = player_dto.state.targets
            targets_count = len(targets)
            charges = player_dto.state.switch_charges
            if targets:
                target_id = targets[0]

        # Форматируем текст дашборда
        p_state_dict = self._extract_player_state(player_dto)
        p_state_dict["switch_charges"] = charges

        text = self.fmt.format_dashboard(
            player_state=p_state_dict,
            target_id=target_id,
            enemies_list=enemies_data,
            allies_list=allies_data,
            timer_text="⏳ <i>Ваш ход...</i>",
        )

        # Строим боевую клавиатуру
        can_switch = charges > 0 and targets_count > 1
        kb = self._build_combat_grid(current_selection, can_switch=can_switch)

        return text, kb

    # =========================================================================
    # 3. ЭКРАНЫ СОСТОЯНИЙ (Результат / Смерть)
    # =========================================================================

    async def _render_results(self, meta: dict) -> tuple[str, InlineKeyboardMarkup]:
        """
        Экран завершения боя.
        """
        winner = meta.get("winner", "none")
        start_time = int(meta.get("start_time", 0))
        end_time = int(meta.get("end_time", time.time()))
        duration = max(0, end_time - start_time)

        # Загружаем свои данные (чтобы показать финальные статы)
        player_dto = await self._get_my_actor_dto()

        if not player_dto:
            return "Ошибка загрузки результатов.", InlineKeyboardBuilder().as_markup()

        text = self.fmt.format_results(player_dto, winner, duration)

        # Кнопка Выхода
        kb = InlineKeyboardBuilder()
        cb_leave = CombatActionCallback(action="leave").pack()
        kb.row(InlineKeyboardButton(text="🔙 Выйти в Хаб", callback_data=cb_leave))

        return text, kb.as_markup()

    def _render_spectator_mode(self, enemies: list, allies: list) -> tuple[str, InlineKeyboardMarkup]:
        """
        Экран смерти (Наблюдатель).
        """
        enemies_text = self.fmt._format_unit_list(enemies, None, is_enemy=True)
        allies_text = ""
        if allies:
            formatted_allies = self.fmt._format_unit_list(allies, None, is_enemy=False)
            allies_text = f"\n\n<b>🔰 Союзники:</b>\n{formatted_allies}"

        text = (
            "💀 <b>ВЫ МЕРТВЫ</b>\n"
            "<i>Вы пали в бою, но ваша душа еще здесь...</i>\n\n"
            f"<b>🆚 Враги:</b>\n{enemies_text}"
            f"{allies_text}\n\n"
            "⏳ <i>Бой продолжается...</i>"
        )

        kb = InlineKeyboardBuilder()
        # Кнопка "Обновить" для режима наблюдателя
        cb_refresh = CombatActionCallback(action="refresh").pack()
        kb.row(InlineKeyboardButton(text="🔄 Наблюдать (Обновить)", callback_data=cb_refresh))

        return text, kb.as_markup()

    # =========================================================================
    # 4. ПРИВАТНЫЕ МЕТОДЫ И ЛОГИКА
    # =========================================================================

    async def _prepare_dashboard_data(self) -> tuple[CombatSessionContainerDTO | None, list[dict], list[dict]]:
        """
        Собирает данные о всех участниках, разделяя их на 'Меня', 'Врагов' и 'Союзников'.
        """
        participant_ids = await combat_manager.get_session_participants(self.session_id)

        player_dto = None
        enemies_data = []
        allies_data = []

        all_actors = []
        my_team = "blue"

        # 1. Загружаем всех
        for pid_str in participant_ids:
            pid = int(pid_str)
            raw = await combat_manager.get_actor_json(self.session_id, pid)
            if raw:
                dto = CombatSessionContainerDTO.model_validate_json(raw)
                all_actors.append(dto)
                if pid == self.char_id:
                    player_dto = dto
                    my_team = dto.team

        # 2. Сортируем
        now = time.time()
        for actor in all_actors:
            # Определяем статус готовности (pending move)
            # Определяем, сделал ли этот участник ход против нас
            pending_move = await combat_manager.get_pending_move(self.session_id, actor.char_id, self.char_id)
            is_ready = bool(pending_move)

            hp_max = 100
            if actor.stats:
                hp_base = actor.stats.get("hp_max", StatSourceData(base=100))
                hp_max = int(StatsCalculator.calculate("hp_max", hp_base))

            info = {
                "char_id": actor.char_id,
                "name": actor.name,
                "hp_current": actor.state.hp_current if actor.state else 0,
                "hp_max": hp_max,
                "is_ready": is_ready,
                "last_action_time": now,
            }

            if actor.char_id == self.char_id:
                continue
            elif actor.team == my_team:
                allies_data.append(info)
            else:
                enemies_data.append(info)

        return player_dto, enemies_data, allies_data

    def _extract_player_state(self, player_dto: CombatSessionContainerDTO | None) -> dict:
        """Конвертирует DTO в dict для форматтера."""
        if not player_dto or not player_dto.state:
            return {"hp_current": 0, "tokens": {}}

        hp_max = int(StatsCalculator.calculate("hp_max", player_dto.stats.get("hp_max", StatSourceData(base=100))))
        en_max = int(
            StatsCalculator.calculate("energy_max", player_dto.stats.get("energy_max", StatSourceData(base=100)))
        )

        return {
            "hp_current": player_dto.state.hp_current,
            "hp_max": hp_max,
            "energy_current": player_dto.state.energy_current,
            "energy_max": en_max,
            "tokens": player_dto.state.tokens,
        }

    def _build_combat_grid(self, selection: dict, can_switch: bool) -> InlineKeyboardMarkup:
        """
        Строит основную клавиатуру боя (Сетка 4x2 + Действия).
        """
        kb = InlineKeyboardBuilder()
        sel_atk = selection.get("atk", [])
        sel_def = selection.get("def", [])

        # 1. Сетка Зон
        rows = [
            ("head", "🗡 Голова", "head_chest", "🛡 Голова + Грудь"),
            ("chest", "🗡 Грудь", "chest_legs", "🛡 Грудь + Живот"),
            ("legs", "🗡 Живот", "legs_feet", "🛡 Живот + Ноги"),
            ("feet", "🗡 Ноги", "feet_head", "🛡 Ноги + Голова"),
        ]

        for atk_id, atk_name, def_id, def_name in rows:
            txt_atk = f"✅ {atk_name}" if atk_id in sel_atk else atk_name
            txt_def = f"✅ {def_name}" if def_id in sel_def else def_name

            cb_atk = CombatZoneCallback(layer="atk", zone_id=atk_id).pack()
            cb_def = CombatZoneCallback(layer="def", zone_id=def_id).pack()

            kb.row(
                InlineKeyboardButton(text=txt_atk, callback_data=cb_atk),
                InlineKeyboardButton(text=txt_def, callback_data=cb_def),
            )

        # 2. Меню Абилок/Предметов
        cb_skills = CombatActionCallback(action="menu").pack()
        kb.row(InlineKeyboardButton(text="⚡ Умения / 🎒 Предметы", callback_data=cb_skills))

        # 3. Смена цели
        if can_switch:
            cb_switch = CombatActionCallback(action="switch_target").pack()
            kb.row(InlineKeyboardButton(text="🔄 Сменить цель (-1 тактика)", callback_data=cb_switch))

        # 4. Подтвердить
        cb_submit = CombatActionCallback(action="submit").pack()
        kb.row(InlineKeyboardButton(text="✅ Подтвердить", callback_data=cb_submit))

        return kb.as_markup()

    async def _get_my_actor_dto(self) -> CombatSessionContainerDTO | None:
        """Хелпер для быстрой загрузки себя из Redis."""
        raw = await combat_manager.get_actor_json(self.session_id, self.char_id)
        if raw:
            return CombatSessionContainerDTO.model_validate_json(raw)
        return None
