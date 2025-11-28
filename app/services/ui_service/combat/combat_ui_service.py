# app/services/ui_service/combat/combat_ui_service.py
import json
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
from app.services.ui_service.base_service import BaseUIService
from app.services.ui_service.helpers_ui.combat_formatters import CombatFormatter


class CombatUIService(BaseUIService):
    """
    Сервис для рендеринга пользовательского интерфейса в бою.

    Отвечает за формирование текста и клавиатур для лога боя (верхнее сообщение)
    и панели управления (нижнее сообщение).
    """

    def __init__(self, user_id: int, char_id: int, session_id: str, state_data: dict[str, Any]):
        """
        Инициализирует UI сервис для боя.

        Args:
            user_id (int): ID пользователя Telegram.
            char_id (int): ID персонажа.
            session_id (str): ID боевой сессии.
            state_data (dict[str, Any]): Данные из FSM.
        """
        super().__init__(state_data=state_data, char_id=char_id)
        self.user_id = user_id
        self.session_id = session_id
        self.fmt = CombatFormatter
        self.LOG_PAGE_SIZE = 5
        log.debug(f"CombatUIService инициализирован для user_id={user_id}, char_id={char_id}, session_id={session_id}")

    # --- ЛОГ БОЯ (Верхнее сообщение) ---
    async def render_combat_log(self, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит лог боя с пагинацией.

        Args:
            page (int): Номер страницы лога для отображения.

        Returns:
            tuple[str, InlineKeyboardMarkup]: Текст лога и клавиатура пагинации.
        """
        log.debug(f"Рендеринг лога боя, страница {page}.")
        all_logs_json = await combat_manager.get_combat_log_list(self.session_id)

        all_logs = []
        for log_json in all_logs_json:
            try:
                all_logs.append(json.loads(log_json))
            except json.JSONDecodeError:
                log.warning(f"Ошибка декодирования записи лога в сессии {self.session_id}: {log_json}")

        text = self.fmt.format_log(all_logs, page, self.LOG_PAGE_SIZE)

        kb = InlineKeyboardBuilder()
        total_items = len(all_logs)
        total_pages = (total_items + self.LOG_PAGE_SIZE - 1) // self.LOG_PAGE_SIZE

        btns = []
        if page < total_pages - 1:
            cb_old = CombatLogCallback(page=page + 1).pack()
            btns.append(InlineKeyboardButton(text="< Ранее", callback_data=cb_old))
        if page > 0:
            cb_new = CombatLogCallback(page=page - 1).pack()
            btns.append(InlineKeyboardButton(text="Позже >", callback_data=cb_new))
        if btns:
            kb.row(*btns)

        return text, kb.as_markup()

    # --- ПАНЕЛЬ УПРАВЛЕНИЯ (Нижнее сообщение) ---

    async def render_dashboard(self, current_selection: dict) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит панель управления боем (дашборд).

        Args:
            current_selection (dict): Текущий выбор зон атаки и защиты.

        Returns:
            tuple[str, InlineKeyboardMarkup]: Текст дашборда и боевая клавиатура.
        """
        log.debug(f"Рендеринг дашборда с выбором: {current_selection}")
        player_state, enemies_list = await self._prepare_dashboard_data()

        text = self.fmt.format_dashboard(
            player_state=player_state,
            enemies_status=enemies_list,
            timer_text="⏳ <i>Ожидание хода...</i>",
        )

        kb = self._build_combat_grid(current_selection)

        return text, kb

    # --- ПРИВАТНЫЕ МЕТОДЫ (Логика и Сборка) ---

    async def _prepare_dashboard_data(self) -> tuple[dict, list[dict]]:
        """Собирает и обрабатывает данные о всех участниках боя из Redis."""
        log.debug("Подготовка данных для дашборда...")
        participant_ids = await combat_manager.get_session_participants(self.session_id)
        player_dto = None
        enemies_data = []

        for pid_str in participant_ids:
            try:
                pid = int(pid_str)
                raw_json = await combat_manager.get_actor_json(self.session_id, pid)
                if not raw_json:
                    log.warning(f"Не найден JSON для участника {pid} в сессии {self.session_id}")
                    continue

                actor = CombatSessionContainerDTO.model_validate_json(raw_json)
                if pid == self.char_id:
                    player_dto = actor
                else:
                    enemies_data.append(await self._process_enemy_status(actor, pid))
            except (ValueError, json.JSONDecodeError) as e:
                log.exception(f"Ошибка обработки участника {pid_str} в сессии {self.session_id}: {e}")

        player_state_dict = self._extract_player_state(player_dto)
        log.debug(f"Данные для дашборда собраны: Игрок: {player_state_dict}, Враги: {len(enemies_data)}")
        return player_state_dict, enemies_data

    async def _process_enemy_status(self, actor: CombatSessionContainerDTO, pid: int) -> dict:
        """Определяет статус врага (думает/готов/мертв) и собирает его данные."""
        pending_move = await combat_manager.get_pending_move(self.session_id, pid)
        status = "ready" if pending_move else "thinking"
        if actor.state and actor.state.hp_current <= 0:
            status = "dead"

        # TODO: [BUG] Некорректный расчет максимального HP.
        #       Используется только базовое значение, игнорируя бонусы от экипировки,
        #       умений и других модификаторов.
        #       Правильный подход: использовать StatsCalculator.aggregate_all()
        #       для получения итогового значения.
        hp_max = 100
        hp_stat = actor.stats.get("hp_max")
        if isinstance(hp_stat, StatSourceData) and hp_stat.base > 0:
            hp_max = int(hp_stat.base)

        return {
            "name": actor.name,
            "hp_current": actor.state.hp_current if actor.state else 0,
            "hp_max": hp_max,
            "status": status,
        }

    def _extract_player_state(self, player_dto: CombatSessionContainerDTO | None) -> dict:
        """Извлекает и форматирует состояние игрока в безопасный словарь."""
        if not player_dto or not player_dto.state:
            log.warning(f"Не найден DTO игрока ({self.char_id}) для извлечения состояния.")
            return {
                "hp_current": 0,
                "hp_max": 0,
                "energy_current": 0,
                "energy_max": 0,
                "tokens": {},
            }

        # TODO: [BUG] Некорректный расчет максимального HP.
        #       Используется только базовое значение, игнорируя бонусы от экипировки,
        #       умений и других модификаторов.
        #       Правильный подход: использовать StatsCalculator.aggregate_all()
        #       для получения итогового значения.
        hp_max = 100
        hp_stat = player_dto.stats.get("hp_max")
        if isinstance(hp_stat, StatSourceData):
            hp_max = int(hp_stat.base)

        # TODO: [BUG] Некорректный расчет максимальной Энергии.
        #       Аналогично HP, используется только базовое значение.
        #       Необходимо использовать StatsCalculator.aggregate_all().
        en_max = 100
        en_stat = player_dto.stats.get("energy_max")
        if isinstance(en_stat, StatSourceData):
            en_max = int(en_stat.base)

        return {
            "hp_current": player_dto.state.hp_current,
            "hp_max": hp_max,
            "energy_current": player_dto.state.energy_current,
            "energy_max": en_max,
            "tokens": player_dto.state.tokens,
        }

    def _build_combat_grid(self, selection: dict) -> InlineKeyboardMarkup:
        """Строит клавиатуру с сеткой зон атаки/защиты и кнопками действий."""
        kb = InlineKeyboardBuilder()
        sel_atk = selection.get("atk", [])
        sel_def = selection.get("def", [])

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

        cb_actions = CombatActionCallback(action="menu").pack()
        cb_submit = CombatActionCallback(action="submit").pack()

        kb.row(InlineKeyboardButton(text="⚡️ Умения", callback_data=cb_actions))
        kb.row(InlineKeyboardButton(text="✅ Подтвердить", callback_data=cb_submit))

        return kb.as_markup()
