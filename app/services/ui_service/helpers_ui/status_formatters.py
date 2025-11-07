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
        log.debug(f"Начало форматирования биографии персонажа. Actor: '{actor_name}'.")
        if not character or not stats:
            log.warning("Отсутствуют данные персонажа или его характеристик для форматирования биографии.")
            return "Ошибка: не удалось загрузить данные персонажа."

        # Безопасно получаем значения характеристик.
        s = getattr(stats, 'strength', 0)
        p = getattr(stats, 'perception', 0)
        e = getattr(stats, 'endurance', 0)
        c = getattr(stats, 'charisma', 0)
        i = getattr(stats, 'intelligence', 0)
        a = getattr(stats, 'agility', 0)
        l = getattr(stats, 'luck', 0)
        log.debug(f"Характеристики персонажа {character.character_id}: S:{s}, P:{p}, E:{e}, C:{c}, I:{i}, A:{a}, L:{l}.")

        name = character.name
        gender = Buttons.GENDER.get(f"gender:{character.gender}", "Не указан")
        # Форматируем дату создания для лучшей читаемости.
        created_date = character.created_at.strftime('%d-%m-%Y %H:%M') if character.created_at else "Неизвестно"
        log.debug(f"Имя: '{name}', Пол: '{gender}', Дата создания: '{created_date}'.")

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
        log.debug(f"Сформирован текст биографии персонажа (длина: {len(text)}).")
        return text
