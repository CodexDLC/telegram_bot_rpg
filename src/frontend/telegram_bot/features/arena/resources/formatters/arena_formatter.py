from src.shared.schemas.arena import ArenaUIPayloadDTO


class ArenaFormatter:
    @staticmethod
    def format_text(payload: ArenaUIPayloadDTO) -> str:
        """
        Формирует финальный текст сообщения.
        """
        text_parts = []

        # Title
        if payload.title:
            text_parts.append(f"<b>{payload.title}</b>")

        # Description
        if payload.description:
            text_parts.append(payload.description)

        # GearScore (если есть)
        if payload.gs is not None:
            text_parts.append(f"\n📊 Ваш GS: <b>{payload.gs}</b>")

        # Opponent (если есть)
        if payload.opponent_name:
            text_parts.append(f"\n⚔️ Противник: <b>{payload.opponent_name}</b>")

        return "\n\n".join(text_parts)

    @staticmethod
    def add_animation(text: str, animation_frame: str) -> str:
        """
        Заменяет плейсхолдер {ANIMATION} на кадр анимации.
        """
        if "{ANIMATION}" in text:
            return text.replace("{ANIMATION}", animation_frame)
        return f"{text}\n\n{animation_frame}"
