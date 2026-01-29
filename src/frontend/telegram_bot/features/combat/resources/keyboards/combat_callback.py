"""
Файл: app/bot/handlers/combats/callbacks.py
Описание: Структуры данных (CallbackData) для боевой системы.
Архитектура: Разделение по типу нагрузки и ответственности (Menu vs Controls vs Flow).
"""

from aiogram.filters.callback_data import CallbackData


class CombatMenuCallback(CallbackData, prefix="c_menu"):
    """
    1. VIEW LAYER (Верхнее сообщение)
    Управление отображением лога, дашборда и настроек.
    Использует edit_message_text (быстрое, без сброса клавиатуры).

    Attributes:
        action (str): Тип действия.
            - 'page': Листание страниц лога.
            - 'refresh': Принудительное обновление статус-бара.
            - 'settings': Переключение флагов отображения (например, скрыть лишнее).
            - 'info': Запрос детальной информации о цели.
        value (Optional[str]): Параметр действия.
            - Номер страницы ('1', 'next').
            - ID настройки ('hide_kb').
            - ID цели для инфо.
    """

    action: str
    value: str | None = None


class CombatControlCallback(CallbackData, prefix="c_ctrl"):
    """
    2. DRAFT LAYER (Нижнее сообщение)
    Управление выбором действий внутри хода (Draft).
    Использует edit_message_reply_markup (мгновенный отклик).

    Структура: Action (Глагол) -> Layer (Контекст) -> Value (Объект)

    Attributes:
        action (str): ЧТО делаем.
            - 'zone': Клик по сетке тела (выбор атаки/защиты).
            - 'nav': Навигация (смена раскладки клавиатуры: Main <-> Skills <-> Items).
            - 'pick': Выбор конкретного элемента в списке (Скилл, Предмет).

        layer (str): ГДЕ делаем (Контекст/Слой).
            - Для zone: 'atk_m' (Main Hand), 'atk_o' (Off Hand), 'def' (Defense).
            - Для nav/pick: 'root' (Главная), 'abil' (Способности), 'item' (Предметы/Пояс).

        value (str): С ЧЕМ взаимодействуем.
            - ID зоны: 'head', 'legs', 'chest'.
            - ID меню: 'skills_tab', 'items_tab', 'back'.
            - ID объекта: 'fireball_v1', 'hp_potion_small'.
    """

    action: str
    layer: str
    value: str


class CombatFlowCallback(CallbackData, prefix="c_flow"):
    """
    3. HEAVY LAYER (Глобальные действия)
    Запуск фазы расчета хода (Commit) или завершение боя.
    Использует сложную логику, анимацию и обновление обоих сообщений.

    Attributes:
        action (str): Команда движку.
            - 'submit': ПОДТВЕРДИТЬ ХОД (Расчет и запись в БД).
            - 'auto': Включить автобой.
            - 'flee': Попытка сбежать.
            - 'surrender': Сдаться.
    """

    action: str
