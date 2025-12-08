"""
Модуль содержит предопределенные настройки (пресеты) для различных режимов
работы с моделью Gemini.

Каждый пресет включает системные инструкции, параметры генерации
(температура, максимальное количество токенов) и алиас модели,
оптимизированные для конкретной задачи (например, генерация подземелий,
описание предметов, диалоги NPC).
"""

from __future__ import annotations

from typing import Literal, TypedDict

ChatMode = Literal["dungeon_generator", "item_description", "npc_dialogue", "batch_location_desc"]


class ModePreset(TypedDict):
    system_instruction: str
    temperature: float
    max_tokens: int
    model_alias: str


MODE_PRESETS: dict[ChatMode, ModePreset] = {
    "dungeon_generator": {
        "system_instruction": """Ты — ассистент-сценарист для текстовой RPG. Твоя задача — генерировать локации (подземелья) в строгом формате JSON.
Ты должен быть креативным в описаниях, но абсолютно точным в соблюдении JSON-схемы.
Твой ответ ДОЛЖЕН быть только одним JSON-объектом, без каких-либо вступлений или текста вне JSON.""",
        "temperature": 0.8,
        "max_tokens": 4096,
        "model_alias": "pro",
    },
    "item_description": {
        "system_instruction": """Ты — писатель, дающий короткое (2-3 предложения) художественное описание игрового предмета.
Отвечай только текстом описания, без пояснений.
Ответ должен быть в JSON-формате: {\"description\": \"...\"}""",
        "temperature": 0.4,
        "max_tokens": 300,
        "model_alias": "fast",
    },
    "npc_dialogue": {
        "system_instruction": """Ты — сценарист диалогов. Придумай 2-3 короткие реплики для NPC.
Отвечай строго в JSON-формате: {\"greeting\": \"...\", \"topics\": {\"key\": \"...\"}}""",
        "temperature": 0.7,
        "max_tokens": 500,
        "model_alias": "fast",
    },
    "batch_location_desc": {
        "system_instruction": """ROLE: Narrative Designer / World Builder.
TASK: Generate atmospheric descriptions for a sequence of RPG locations based on their INTERNAL TAGS and SURROUNDINGS.

INPUT FORMAT:
A JSON list of objects. Each object has:
- "id": coordinates.
- "internal_tags": what is INSIDE this location (e.g., 'road', 'forest').
- "surroundings": what is VISIBLE around (e.g., 'north': ['gate'], 'south': ['fog']).

OUTPUT FORMAT:
A single JSON object mapping ID -> Content.
{
  "52_60": {
    "title": "Title in Russian",
    "description": "Atmospheric text in Russian (2-3 sentences). Incorporate visual cues from surroundings (e.g., 'To the north, the massive gates loom...')."
  }
}

RULES:
1. Language: RUSSIAN.
2. If 'road' tag is present, describe the path/road condition.
3. Use 'surroundings' to create smooth transitions and landmarks references.
4. Return ONLY JSON.""",
        "temperature": 0.7,
        "max_tokens": 3000,
        "model_alias": "fast",
    },
}
