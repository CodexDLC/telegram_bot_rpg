# app/services/ui_service/helpers_ui/combat_formatters.py
from loguru import logger as log

from app.resources.schemas_dto.combat_source_dto import CombatSessionContainerDTO


class CombatFormatter:
    """
    Статический класс для форматирования текста в бою.
    v2: Группировка по командам, маркер цели, инлайн-статусы, экран результатов.
    """

    @staticmethod
    def format_log(all_logs: list[dict], page: int, page_size: int) -> str:
        """
        Форматирует лог боя с пагинацией.
        """
        if not all_logs:
            log.debug("Форматирование лога: лог пуст.")
            return "⚔️ <b>Бой начинается...</b>\n<i>Ожидание первого обмена ударами.</i>"

        total_logs = len(all_logs)
        total_pages = (total_logs + page_size - 1) // page_size

        end_idx = total_logs - (page * page_size)
        start_idx = max(0, end_idx - page_size)

        if end_idx <= 0:
            return "📜 <i>История пуста или недоступна.</i>"

        chunk = all_logs[start_idx:end_idx]

        text_lines = [f"📜 <b>Хроника (Стр. {page + 1}/{total_pages}):</b>\n"]

        for entry in chunk:
            idx = entry.get("round_index", 0)
            logs_list = entry.get("logs", [])

            # 🔥 ДОСТАЕМ ИМЕНА 🔥
            pair_names = entry.get("pair_names", [])
            if len(pair_names) >= 2:
                # Если имена есть: "--- Обмен 1: Герой и Манекен ---"
                header_text = f"<b>--- Обмен {idx}: {pair_names[0]} и {pair_names[1]} ---</b>"
            else:
                # Фоллбэк, если имен нет (старые логи)
                header_text = f"<b>--- Обмен {idx} ---</b>"

            text_lines.append(header_text)
            text_lines.extend(logs_list)
            text_lines.append("")  # Пустая строка

        return "\n".join(text_lines)

    @staticmethod
    def format_dashboard(
        player_state: dict,
        target_id: int | None,  # ID текущей цели
        enemies_list: list[dict],
        allies_list: list[dict],
        timer_text: str,
    ) -> str:
        """
        Форматирует текст для панели управления боем (дашборда).
        v3.0: Детальный вывод всех токенов с уникальными иконками + разделение команд.
        """
        # --- Состояние игрока ---
        hp_cur = int(player_state.get("hp_current", 0))
        hp_max = int(player_state.get("hp_max", 1))
        en_cur = int(player_state.get("energy_current", 0))
        en_max = int(player_state.get("energy_max", 0))

        # --- Токены (Разбираем словарь) ---
        tokens = player_state.get("tokens", {})

        # Атакующие
        t_hit = tokens.get("hit", 0)
        t_crit = tokens.get("crit", 0)

        # Защитные
        t_block = tokens.get("block", 0)
        t_parry = tokens.get("parry", 0)
        t_counter = tokens.get("counter", 0)

        # Заряды смены
        charges = player_state.get("switch_charges", 0)

        # Формируем строку токенов (разбиваем на 2 строки для читаемости на телефоне)
        # Строка 1: Атака
        tokens_atk_str = f"🗡 <b>{t_hit}</b>  💥 <b>{t_crit}</b>"
        # Строка 2: Защита
        tokens_def_str = f"🛡 <b>{t_block}</b>  ⚔️ <b>{t_parry}</b>  ↩️ <b>{t_counter}</b>"

        header = (
            f"👤 <b>Вы:</b> {hp_cur}/{hp_max} HP | {en_cur}/{en_max} EN\n"
            f"💎 <b>Токены:</b>\n"
            f"[ {tokens_atk_str} ]\n"
            f"[ {tokens_def_str} ]\n"
            f"🔄 <b>Тактика:</b> {charges} зарядов"
        )

        # 2. Секция Врагов
        enemies_text = CombatFormatter._format_unit_list(enemies_list, target_id, is_enemy=True)

        # 3. Секция Союзников
        allies_text = ""
        if allies_list:
            allies_text = "\n\n<b>🔰 Союзники:</b>\n" + CombatFormatter._format_unit_list(
                allies_list, None, is_enemy=False
            )

        # --- Сборка финального текста ---
        text = (
            f"{header}\n\n"
            f"<b>🆚 Противники:</b>\n"
            f"{enemies_text}"
            f"{allies_text}\n\n"
            f"--------------------------\n"
            f"{timer_text}"
        )
        log.debug("Дашборд отформатирован (Full Token View + Teams).")
        return text

    @staticmethod
    def _format_unit_list(units: list[dict], target_id: int | None, is_enemy: bool) -> str:
        lines = []

        for unit in units:
            uid = unit["char_id"]
            name = unit["name"]
            hp_cur = unit["hp_current"]
            hp_max = unit["hp_max"]

            # Статус (Жив/Мертв)
            if hp_cur <= 0:
                status_icon = "💀"
                hp_display = "[МЕРТВ]"
            else:
                # Статус готовности (pending move)
                is_ready = unit.get("is_ready", False)
                status_icon = "✅" if is_ready else "⏳"
                hp_perc = int((hp_cur / hp_max) * 100) if hp_max > 0 else 0
                hp_display = f"{hp_cur} HP ({hp_perc}%)"

            # Маркер цели (Только для врагов)
            target_marker = ""
            if is_enemy and target_id == uid:
                target_marker = "🎯 <b>ЦЕЛЬ</b> "
                name = f"<u>{name}</u>"  # Подчеркиваем текущую цель

            lines.append(f"{status_icon} {target_marker}<b>{name}</b>: {hp_display}")

        if not lines:
            return "<i>Никого нет...</i>"

        return "\n".join(lines)

    @staticmethod
    def format_results(player_dto: CombatSessionContainerDTO, winner_team: str, duration: int) -> str:
        """
        Форматирует экран завершения боя.
        TODO: В будущем заменить на BattleResultService для разных режимов (Арена/Босс).
        """
        is_winner = player_dto.team == winner_team

        if is_winner:
            header = "🏆 <b>ПОБЕДА!</b>"
            flavor = "<i>Враг повержен. Вы вытираете кровь с клинка...</i>"
        else:
            header = "💀 <b>ПОРАЖЕНИЕ...</b>"
            flavor = "<i>Тьма сгущается перед глазами. Вы пали в бою.</i>"

        # Достаем статистику
        s = player_dto.state.stats if player_dto.state else None

        stats_text = ""
        if s:
            stats_text = (
                f"<b>📊 Ваша эффективность:</b>\n"
                f"<code>"
                f"⚔️ Урон:    {s.damage_dealt}\n"
                f"🛡 Блок:    {s.blocks_success}\n"
                f"🏃 Уворот:  {s.dodges_success}\n"
                f"💔 Получено: {s.damage_taken}\n"
                f"💥 Критов:   {s.crits_landed}"
                f"</code>"
            )

        return f"{header}\n⏱ <i>Время боя: {duration} сек.</i>\n\n{flavor}\n\n{stats_text}"
