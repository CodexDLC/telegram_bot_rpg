# app/services/helpers_module/tutorial_utils.py

import random
import logging

from app.resources.keyboards.inline_kb.loggin_und_new_character import tutorial_kb
from app.resources.texts.game_messages.tutorial_messages import TutorialEventsData

log = logging.getLogger(__name__)

def get_event_pool(number: int = 4):
    """
    Возвращает 4 случайных события из пула событий
    """

    TUTORIAL_EVENT_POOL = TutorialEventsData.TUTORIAL_EVENT_POOL

    event_pool = random.sample(TUTORIAL_EVENT_POOL, number)

    log.debug(f"Список из {number} случайных событий: {event_pool}")
    return event_pool


def prepare_tutorial_step(event_pool: list, sim_text_count: int, count_event: int = 4):
    """
    Готовит данные для ОДНОГО шага туториала.
    """

    if sim_text_count == 0:
        event_pool = get_event_pool()


    # 1. Увеличиваем счетчик шага
    sim_text_count += 1


    # 2. (БЕЗ ELSE) Извлекаем СЛЕДУЮЩИЙ ивент из пула
    try:
        event = event_pool.pop(0)
    except IndexError:
        # VVV ВОТ ТВОЕ РЕШЕНИЕ VVV
        log.debug("prepare_tutorial_step: Пул событий пуст. Сигнализируем о завершении.")
        # Возвращаем "пустые" данные, которые хэндлер сможет проверить
        return None, None, sim_text_count, event_pool

    # 3. Готовим данные (Этот код выполнится, только если .pop() сработал)
    text_event = event.get("text", "")
    kb_data = event.get("buttons", {})

    sim_text_template = TutorialEventsData.SIMULATION_TEXT_TEMPLATE
    text = sim_text_template.format(number=sim_text_count, text_event=text_event)

    kb = tutorial_kb(kb_data)

    return text, kb, sim_text_count, event_pool



def summ_stat_bonus(key: str, bonus_dict: dict):
    data = TutorialEventsData.TUTORIAL_LOGIC_POOL
    bonus = data.get(key)
    if bonus:
        for stat, bonus_value in bonus.items():
            if stat in bonus_dict:
                bonus_dict[stat] += bonus_value
            else:
                bonus_dict[stat] = bonus_value

    return bonus_dict

