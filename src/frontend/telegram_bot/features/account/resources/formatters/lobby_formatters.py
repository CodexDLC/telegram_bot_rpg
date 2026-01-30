from src.shared.schemas.character import CharacterReadDTO


class LobbyFormatter:
    """
    Форматирование текста для Lobby.
    """

    GENDER_MAP = {
        "male": "♂ Мужской",
        "female": "♀ Женский",
        "other": "⚧ Другой",
    }

    GAME_STAGE_MAP = {
        "lobby": "В лобби",
        "onboarding": "Создание персонажа",
        "combat": "⚔️ В бою",
        "scenario": "📜 В сценарии",
        "exploration": "🗺 В путешествии",
    }

    @staticmethod
    def format_menu_message(characters: list[CharacterReadDTO] | None) -> str:
        """
        Текст для верхнего сообщения (menu) — список персонажей.
        """
        if not characters:
            return "🏰 <b>Лобби</b>\n\nУ тебя пока нет персонажей.\nСоздай своего первого героя!"

        header = "🏰 <b>Лобби</b>\n\n"
        header += f"Персонажей: {len(characters)}/4\n"
        header += "Выбери персонажа для игры:"

        return header

    @staticmethod
    def format_delete_confirm(char_name: str) -> str:
        """
        Текст подтверждения удаления.
        """
        return f"⚠️ <b>Удаление персонажа</b>\n\nТы уверен, что хочешь удалить <b>{char_name}</b>?\n\nЭто действие необратимо!"

    @staticmethod
    def format_character_card(char: CharacterReadDTO) -> str:
        """
        Карточка персонажа (content при select).
        """
        gender = LobbyFormatter.GENDER_MAP.get(char.gender, char.gender)
        stage = LobbyFormatter.GAME_STAGE_MAP.get(char.game_stage, char.game_stage)

        lines = [
            f"👤 <b>{char.name}</b>",
            f"Пол: {gender}",
            "",
        ]

        # Vitals (если не lobby/onboarding)
        if char.game_stage not in ("lobby", "onboarding") and char.vitals_snapshot:
            vitals = char.vitals_snapshot
            if "hp" in vitals:
                hp = vitals["hp"]
                lines.append(f"❤️ HP: {hp.get('cur', 0)}/{hp.get('max', 0)}")
            if "mp" in vitals:
                mp = vitals["mp"]
                lines.append(f"💙 MP: {mp.get('cur', 0)}/{mp.get('max', 0)}")
            if "stamina" in vitals:
                stamina = vitals["stamina"]
                lines.append(f"⚡ Stamina: {stamina.get('cur', 0)}/{stamina.get('max', 0)}")
            lines.append("")

        # Статус
        lines.append(f"📍 {stage}")

        return "\n".join(lines)
