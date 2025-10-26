import types
from typing import Callable, Tuple, List, Any, Union

from app.resources.llm_data.json_sheme import DUNGEON_JSON_SCHEMA_PROMPT
from app.resources.llm_data.mode_preset import ModePreset, ChatMode


def build_simple_gemini(
        preset: ModePreset,
        user_text: str,  # Это будет "Название предмета" или "Тема диалога"
        **kw: Any
) -> tuple[str, str]:
    """
    Универсальный строитель для простых задач.
    Берет system_instruction из пресета и user_text.
    """
    system_instruction = preset["system_instruction"]
    contents = user_text
    return contents, system_instruction


def build_dungeon_gemini(
        preset: ModePreset,
        user_text: str,  # (Этот параметр будет проигнорирован)
        **kw: Any
) -> tuple[str, str]:
    """
    Специальный строитель для генерации подземелий.
    Игнорирует user_text, но берет theme_prompt_from_db из **kw.
    """
    theme_prompt_from_db = kw.get("theme_prompt_from_db", "")
    base_instruction = preset["system_instruction"]

    final_instruction = f"""
{base_instruction}

ЗАДАЧА:
{theme_prompt_from_db}

ТРЕБОВАНИЯ К ФОРМАТУ:
{DUNGEON_JSON_SCHEMA_PROMPT}
"""
    contents = ""  # user_text не нужен
    return contents, final_instruction

# 3. Создаем тип, который может быть ИЛИ строкой, ИЛИ списком (на будущее)
GeminiContents = Union[str, List[types.Content]]

# Builder теперь ожидает `str` ИЛИ `List` в качестве первого элемента
GeminiBuilder = Callable[..., Tuple[GeminiContents, str]]


BUILDERS_GEMINI: dict[ChatMode, GeminiBuilder] = {
    "dungeon_generator": build_dungeon_gemini,
    "item_description": build_simple_gemini,
    # "npc_dialogue": build_npc_dialogue,
}