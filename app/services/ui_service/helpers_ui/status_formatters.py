# app/services/ui_service/helpers_ui/status_formatters.py
import logging
from typing import Optional

from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO, CharacterReadDTO
from app.resources.texts.buttons_callback import Buttons

log = logging.getLogger(__name__)


class StatusFormatter:
    """
    Класс-контейнер для статических методов форматирования текста в меню статуса.
    """

    @staticmethod
    def format_character_bio(
            character: Optional[CharacterReadDTO],
            stats: Optional[CharacterStatsReadDTO],
            actor_name: str
    ) -> str:
        """
        Форматирует текст для вкладки "Биография" в меню статуса.

        Создает подробное описание персонажа, включая его имя, пол,
        характеристики (S.P.E.C.I.A.L.) и дату создания.

        Args:
            character (Optional[CharacterReadDTO]): DTO с основной
                информацией о персонаже.
            stats (Optional[CharacterStatsReadDTO]): DTO с характеристиками
                персонажа.
            actor_name (str): Имя "рассказчика".

        Returns:
            str: Отформатированный текст для сообщения.
        """
        if not character or not stats:
            log.warning("Отсутствуют данные персонажа или его характеристик.")
            return "Ошибка: не удалось загрузить данные персонажа."

        # Безопасно получаем значения характеристик, используя getattr
        # с fallback-значением 0, если атрибут отсутствует.
        s = getattr(stats, 'strength', 0)
        p = getattr(stats, 'perception', 0)
        e = getattr(stats, 'endurance', 0)
        c = getattr(stats, 'charisma', 0)
        i = getattr(stats, 'intelligence', 0)
        a = getattr(stats, 'agility', 0)
        l = getattr(stats, 'luck', 0)

        name = character.name
        gender = Buttons.GENDER.get(f"gender:{character.gender}", "Не указан")
        # Форматируем дату создания для лучшей читаемости.
        created_date = character.created_at.strftime('%d-%m-%Y %H:%M') if character.created_at else "Неизвестно"

        # Используем f-string с тройными кавычками для удобного
        # многострочного форматирования.
        text = (
            f"{actor_name}: ❗ Инициация данных\n"
            f"{actor_name}: Вывод данных.\n\n"
            f"<code>"
            f"ℹ️ Статус персонажа:  -= <i>{name}</i> =-\n\n"
            f"<b>Пол:</b> <i>{gender}</i>\n"
            f"<b>Параметры персонажа:</b>\n"
            f"  (Сила).........: {s}\n"
            f"  (Восприятие)...: {p}\n"
            f"  (Выносливость).: {e}\n"
            f"  (Харизма)......: {c}\n"
            f"  (Интеллект)....: {i}\n"
            f"  (Ловкость).....: {a}\n"
            f"  (Удача)........: {l}\n\n"
            f"<b>Дата создания:</b> <i>{created_date}</i>\n"
            f"</code>"
        )
        return text
