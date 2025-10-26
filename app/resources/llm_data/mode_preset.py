# app/resources/assets/game_presets.py (новое название)
from __future__ import annotations
from typing import Dict, Literal, TypedDict

# Наши новые "игровые" режимы
ChatMode = Literal["dungeon_generator", "item_description", "npc_dialogue"]

class ModePreset(TypedDict):
    # Одно, главное поле для инструкции
    system_instruction: str
    temperature: float
    max_tokens: int
    model_alias: str

# Мы просто объединяем "developer" и "system" в одно поле
MODE_PRESETS: Dict[ChatMode, ModePreset] = {
    "dungeon_generator": {
        "system_instruction": """Ты — ассистент-сценарист для текстовой RPG. Твоя задача — генерировать локации (подземелья) в строгом формате JSON.
Ты должен быть креативным в описаниях, но абсолютно точным в соблюдении JSON-схемы.
Твой ответ ДОЛЖЕН быть только одним JSON-объектом, без каких-либо вступлений или текста вне JSON.""",
        "temperature": 0.8,
        "max_tokens": 4096,
        "model_alias": "pro"
    },
    "item_description": {
        "system_instruction": """Ты — писатель, дающий короткое (2-3 предложения) художественное описание игрового предмета.
Отвечай только текстом описания, без пояснений.
Ответ должен быть в JSON-формате: {\"description\": \"...\"}""",
        "temperature": 0.4,
        "max_tokens": 300,
        "model_alias": "fast"
    },
    "npc_dialogue": {
        "system_instruction": """Ты — сценарист диалогов. Придумай 2-3 короткие реплики для NPC.
Отвечай строго в JSON-формате: {\"greeting\": \"...\", \"topics\": {\"key\": \"...\"}}""",
        "temperature": 0.7,
        "max_tokens": 500,
        "model_alias": "fast"
    },
}