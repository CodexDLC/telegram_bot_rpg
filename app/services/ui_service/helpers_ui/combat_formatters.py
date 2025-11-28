# app/services/ui_service/helpers_ui/combat_formatters.py

from loguru import logger as log


class CombatFormatter:
    """
    Статический класс для форматирования текста в бою.

    Предоставляет методы для создания текстового представления лога боя
    и панели управления (дашборда).
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
    def format_dashboard(player_state: dict, enemies_status: list[dict], timer_text: str) -> str:
        """
        Форматирует текст для панели управления боем (дашборда).

        Args:
            player_state (dict): Словарь с состоянием игрока (HP, Energy, токены).
            enemies_status (list[dict]): Список словарей с состоянием врагов.
            timer_text (str): Текст таймера или статуса хода.

        Returns:
            str: Отформатированный текст для сообщения с дашбордом.
        """
        # --- Состояние игрока ---
        hp_cur = int(player_state.get("hp_current", 0))
        hp_max = int(player_state.get("hp_max", 1))  # Избегаем деления на ноль
        en_cur = int(player_state.get("energy_current", 0))
        en_max = int(player_state.get("energy_max", 0))

        tokens = player_state.get("tokens", {})
        tok_atk = tokens.get("offense", 0)
        tok_def = tokens.get("defense", 0)

        # --- Состояние врагов ---
        enemies_text_lines = []
        if not enemies_status:
            enemies_text_lines.append("<i>Нет противников</i>")
        else:
            for i, enemy in enumerate(enemies_status, 1):
                icon_map = {"thinking": "🔴", "ready": "🟢", "dead": "💀"}
                status = enemy.get("status", "thinking")
                icon = icon_map.get(status, "❓")

                name = enemy.get("name", "Враг")
                e_hp = enemy.get("hp_current", 0)
                e_max = enemy.get("hp_max", 1)  # Избегаем деления на ноль
                hp_perc = int((e_hp / e_max) * 100) if e_max > 0 else 0

                enemies_text_lines.append(f"{i}. {icon} <b>{name}</b> [{hp_perc}% HP]")

        enemies_text = "\n".join(enemies_text_lines)

        # --- Сборка финального текста ---
        text = (
            f"👤 <b>Вы:</b> {hp_cur}/{hp_max} HP | {en_cur}/{en_max} EN\n"
            f"💎 <b>Тактика:</b> [🔴 {tok_atk}] [🔵 {tok_def}]\n\n"
            f"🆚 <b>Противники:</b>\n"
            f"{enemies_text}\n"
            f"--------------------------\n"
            f"{timer_text}"
        )
        log.debug("Дашборд отформатирован.")
        return text
