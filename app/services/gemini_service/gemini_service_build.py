# app/services/gemini_service/gemini_service_build.py
import logging
from typing import Callable, Tuple, List, Any, Union, Dict
from google.generativeai import types

from app.resources.llm_data.json_sheme import DUNGEON_JSON_SCHEMA_PROMPT
from app.resources.llm_data.mode_preset import ModePreset, ChatMode

log = logging.getLogger(__name__)

# Определяем тип для содержимого, которое может быть строкой или списком.
GeminiContents = Union[str, List[types.ContentDict]]
# Определяем тип для функции-сборщика.
GeminiBuilder = Callable[..., Tuple[GeminiContents, str]]


def build_simple_gemini(
        preset: ModePreset,
        user_text: str,
        **kw: Any
) -> Tuple[GeminiContents, str]:
    """
    Универсальный сборщик для простых текстовых задач.

    Формирует промпт, используя `system_instruction` из пресета и
    `user_text` в качестве основного содержимого.

    Args:
        preset (ModePreset): Пресет с настройками для модели.
        user_text (str): Основной текст для промпта (например, тема диалога).
        **kw: Дополнительные параметры (не используются в этом сборщике).

    Returns:
        Tuple[GeminiContents, str]: Кортеж из содержимого и системной инструкции.
    """
    log.debug(f"Используется 'build_simple_gemini' для режима '{preset.get('name', 'unknown')}'.")
    system_instruction = preset["system_instruction"]
    contents = user_text
    return contents, system_instruction


def build_dungeon_gemini(
        preset: ModePreset,
        user_text: str,  # Этот параметр игнорируется
        **kw: Any
) -> Tuple[GeminiContents, str]:
    """
    Специализированный сборщик для генерации подземелий.

    Формирует сложный промпт, комбинируя базовую инструкцию из пресета,
    тему подземелья из `**kw` и требования к JSON-схеме.

    Args:
        preset (ModePreset): Пресет для генерации подземелий.
        user_text (str): Игнорируется.
        **kw: Должен содержать `theme_prompt_from_db` (строка с темой).

    Returns:
        Tuple[GeminiContents, str]: Кортеж из пустого содержимого и
                                    финальной системной инструкции.
    """
    log.debug("Используется 'build_dungeon_gemini'.")
    theme_prompt_from_db = kw.get("theme_prompt_from_db")
    if not theme_prompt_from_db:
        log.warning("'theme_prompt_from_db' не предоставлен для 'build_dungeon_gemini'. Результат может быть непредсказуемым.")
        theme_prompt_from_db = "Случайная тема на усмотрение ИИ."

    base_instruction = preset["system_instruction"]

    # Собираем финальную инструкцию из нескольких частей.
    final_instruction = f"""
{base_instruction}

ЗАДАЧА:
{theme_prompt_from_db}

ТРЕБОВАНИЯ К ФОРМАТУ:
{DUNGEON_JSON_SCHEMA_PROMPT}
"""
    # Для таких задач, где вся информация в system prompt, user_text может быть пустым.
    contents = ""
    log.debug(f"Сформирована инструкция для 'build_dungeon_gemini' с темой: '{theme_prompt_from_db[:50]}...'")
    return contents, final_instruction


# Словарь, который сопоставляет режимы чата с их функциями-сборщиками.
# Это позволяет гибко добавлять новые режимы и их логику сборки промптов.
BUILDERS_GEMINI: Dict[ChatMode, GeminiBuilder] = {
    "dungeon_generator": build_dungeon_gemini,
    "item_description": build_simple_gemini,
    # "npc_dialogue": build_npc_dialogue, # Пример для будущего расширения
}
log.debug(f"Зарегистрировано {len(BUILDERS_GEMINI)} сборщиков Gemini.")
