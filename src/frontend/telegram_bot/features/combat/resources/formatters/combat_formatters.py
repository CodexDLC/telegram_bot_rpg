# app/services/ui_service/helpers_ui/combat_formatters.py


class CombatFormatter:
    """
    Форматтер для боевых сообщений (RBC v3.0).
    Стиль: 3 блока (Игрок, Цель/Ожидание, Списки).
    """

    @staticmethod
    def format_log(logs_chunk: list[dict], current_page: int, total_pages: int) -> str:
        """
        Форматирует страницу лога.
        logs_chunk: Список записей (уже обрезанный под страницу).
        current_page: Номер текущей страницы (1-based).
        total_pages: Всего страниц.
        """
        if not logs_chunk:
            return "⚔️ <b>Бой начинается...</b>\n<i>Ожидание первого обмена ударами.</i>"

        text_lines = [f"📜 <b>Хроника (Стр. {current_page}/{total_pages}):</b>\n"]

        for entry in logs_chunk:
            text = entry.get("text", "")
            tags = entry.get("tags", [])
            icon = "🔹"
            if "CRIT" in tags:
                icon = "💥"
            elif "MISS" in tags:
                icon = "💨"
            elif "HEAL" in tags:
                icon = "💚"
            elif "KILL" in tags:
                icon = "💀"

            text_lines.append(f"{icon} {text}")

        return "\n".join(text_lines)

    @staticmethod
    def format_dashboard(
        player_state: dict,
        target_state: dict | None,
        enemies_list: list[dict],
        allies_list: list[dict],
        timer_text: str,
    ) -> str:
        """
        Формирует главный экран боя.
        player_state: dict (ActorFullInfo)
        target_state: dict (ActorFullInfo) or None
        """
        # --- БЛОК 1: ИГРОК ---
        hero_text = CombatFormatter._format_actor_block(player_state, is_hero=True)

        # --- БЛОК 2: ЦЕЛЬ или ОЖИДАНИЕ ---
        target_text = ""

        if target_state:
            # Полная инфа о цели
            target_text = CombatFormatter._format_actor_block(target_state, is_hero=False)
        else:
            # Плейсхолдер для анимации
            target_text = "{ANIMATION}"

        # --- БЛОК 3: СПИСКИ (Строчно) ---
        enemies_str = CombatFormatter._format_unit_list_inline(enemies_list)
        allies_str = CombatFormatter._format_unit_list_inline(allies_list)

        text = (
            f"{hero_text}\n\n"
            f"{target_text}\n\n"
            f"🆚 <b>Враги:</b> {enemies_str}\n"
            f"🔰 <b>Свои:</b> {allies_str}\n\n"
            f"--------------------------\n"
            f"{timer_text}"
        )
        return text

    @staticmethod
    def _format_actor_block(actor: dict, is_hero: bool) -> str:
        """Форматирует блок полной информации об акторе."""
        name = actor.get("name", "Unknown")
        hp_cur = actor.get("hp_current", 0)
        hp_max = actor.get("hp_max", 1)
        en_cur = actor.get("energy_current", 0)
        en_max = actor.get("energy_max", 0)
        tokens = actor.get("tokens", {})
        effects = actor.get("effects", [])

        icon = "👤" if is_hero else "👾"

        # Токены
        token_map = {
            "tactics": "🧠",
            "tempo": "⚡",
            "hit": "🗡",
            "crit": "💥",
            "block": "🛡",
            "parry": "⚔️",
            "dodge": "💨",
            "counter": "↩️",
        }
        token_parts = []
        for key, val in tokens.items():
            if val > 0:
                t_icon = token_map.get(key, "🔹")
                token_parts.append(f"{t_icon} {val}")
        tokens_str = ", ".join(token_parts) if token_parts else "<i>нет</i>"

        # Статусы
        effects_str = ", ".join(effects) if effects else "<i>нет</i>"

        return (
            f"{icon} <b>{name}</b> [HP: {hp_cur}/{hp_max} | EN: {en_cur}/{en_max}]\n💎 {tokens_str}\n🌀 {effects_str}"
        )

    @staticmethod
    def _format_unit_list_inline(units: list[dict]) -> str:
        """Форматирует список юнитов в одну строку через запятую."""
        if not units:
            return "<i>никого</i>"

        parts = []
        for unit in units:
            name = unit.get("name", "Unknown")
            hp_perc = unit.get("hp_percent", 0)
            is_dead = unit.get("is_dead", False)

            if is_dead:
                parts.append(f"💀 {name}")
            else:
                parts.append(f"{name} ({hp_perc}%)")

        return ", ".join(parts)

    @staticmethod
    def format_skills_menu(actor, active_skills: list[str]) -> str:
        name = getattr(actor, "name", "Hero")
        text = f"⚡ <b>Дары и Способности ({name})</b>\n\nВыберите способность для использования:"
        if not active_skills:
            text += "\n\n<i>Нет активных способностей.</i>"
        else:
            text += "\n"
            for skill in active_skills:
                text += f"• {skill}\n"
        return text
