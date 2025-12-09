class NavigationFormatter:
    """
    Форматтер для сборки композитного сообщения навигации.
    """

    @staticmethod
    def format_composite_message(
        actor_name: str,
        loc_name: str,
        loc_desc: str,
        xy_coord: str,
        threat_data: dict,
        visual_objects: list[str],
        players_count: int,
        active_battles: int,
        exits_data: dict,  # <--- [NEW] Передаем словарь выходов
        current_loc_id: str,  # <--- [NEW] Для расчета направлений
        system_buttons_legend: str | None = None,
    ) -> str:
        # --- БЛОК 1: ХЕДЕР ---
        header = f"📍 <b>{loc_name}</b> <code>[{xy_coord}]</code>"

        # --- БЛОК 2: НАРРАТИВ ---
        narrative_parts = [f"<i>{loc_desc}</i>"]

        if visual_objects:
            narrative_parts.append("")
            for obj in visual_objects:
                narrative_parts.append(f"🏛 <b>{obj}</b>")

        if active_battles > 0:
            narrative_parts.append(f"\n💬 <b>{actor_name}:</b> <i>«Внимание! Слышу бой ({active_battles})...»</i>")

        narrative_block = "\n".join(narrative_parts)

        # --- БЛОК 3: HUD СИМБИОТА ---
        threat_icon = threat_data.get("emoji", "⚪️")
        threat_label = threat_data.get("label", "UNKNOWN")
        hud_header = f"[ 📟 {actor_name.upper()}: {threat_icon} {threat_label} ]"

        players_display = f"{players_count}" if players_count > 0 else "None"
        hud_signatures = f"[ 📡 Signatures: {players_display} ]"

        hud_block = f"<code>{hud_header.center(28)}\n{hud_signatures.center(28)}</code>"

        # --- БЛОК 4: КОМПАС (НАВИГАЦИЯ) --- [NEW]
        # Формируем список направлений
        compass_block = NavigationFormatter._format_compass(exits_data, current_loc_id)

        # --- СБОРКА ---
        sections = [
            header,
            " ",
            narrative_block,
            " ",
            hud_block,
            " ",
            compass_block,  # Вставляем компас в конце
        ]

        if system_buttons_legend:
            sections.append(f"\n<span class='tg-spoiler'>{system_buttons_legend}</span>")

        return "\n".join(sections)

    @staticmethod
    def _format_compass(exits: dict, current_loc_id: str) -> str:
        """
        Собирает текстовый блок с описанием направлений.
        """
        try:
            cx, cy = map(int, current_loc_id.split("_"))
        except ValueError:
            return ""

        # Шаблон отображения (Порядок как в клавиатуре или логический список)
        # (dx, dy, Emoji, Label)
        # Y уменьшается вверх (0, -1 = Север)
        directions = [
            (0, -1, "⬆️", "Север"),
            (-1, 0, "⬅️", "Запад"),
            (1, 0, "➡️", "Восток"),
            (0, 1, "⬇️", "Юг"),
        ]

        lines = ["<b>🧭 Навигация:</b>"]

        # Словарь найденных выходов: {(dx, dy): "Описание"}
        found_exits = {}

        for key, data in exits.items():
            if not isinstance(data, dict):
                continue

            # Парсим ID
            tid = key.split(":", 1)[1] if ":" in key else key

            try:
                tx, ty = map(int, tid.split("_"))
                dx = tx - cx
                dy = ty - cy
                # Берем описание соседней комнаты (desc_next_room)
                desc = data.get("desc_next_room", "Путь")
                found_exits[(dx, dy)] = desc
            except ValueError:
                continue

        # Сборка строк
        for dx, dy, icon, label in directions:
            if (dx, dy) in found_exits:
                # Если выход есть -> красивое описание
                target_name = found_exits[(dx, dy)]
                lines.append(f"{icon} {label}: <i>{target_name}</i>")
            else:
                # Если выхода нет -> "Красная строка" (Заглушка)
                # Используем ⛔️ или 🧱
                lines.append(f"⛔️ {label}: <code>---</code>")

        return "\n".join(lines)

    @staticmethod
    def get_threat_info(tier: int) -> dict:
        if tier == 0:
            return {"emoji": "🟢", "label": "SAFE"}
        elif tier <= 2:
            return {"emoji": "🟡", "label": "LOW"}
        elif tier <= 4:
            return {"emoji": "🟠", "label": "MED"}
        elif tier <= 6:
            return {"emoji": "🔴", "label": "HIGH"}
        else:
            return {"emoji": "⚫", "label": "ANOMALY"}
