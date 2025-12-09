from typing import Literal

# Словарь режимов работы чата с Gemini
MODE_PRESETS = {
    "dungeon_generator": {
        "system_instruction": """You are an expert game designer creating a dungeon for a dark fantasy RPG.
Generate a dungeon map as a JSON object based on the user's theme.
The map should be a list of rooms, each with an ID, name, description, and connections to other rooms.
The final room must be a 'boss_room'.
Return ONLY the JSON object.""",
        "temperature": 0.8,
        "max_tokens": 2048,
        "model_alias": "fast",
    },
    "item_description": {
        "system_instruction": """You are a creative writer for a dark fantasy RPG.
Write a short, atmospheric description for an item based on its name and tags.
The description should be 2-3 sentences long.
Format the output as a JSON object: {"description": "your text"}.
Return ONLY the JSON object.""",
        "temperature": 0.7,
        "max_tokens": 256,
        "model_alias": "fast",
    },
    "npc_dialogue": {
        "system_instruction": """You are an NPC in a dark fantasy RPG.
Your personality is defined by the tags provided by the user.
Respond to the user's message in character, keeping your response to 2-3 sentences.
Format the output as a JSON object: {"dialogue": "your text"}.
Return ONLY the JSON object.""",
        "temperature": 0.9,
        "max_tokens": 256,
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
A single JSON object mapping ID -> Content. The content object must contain a 'content' key.
{
  "52_60": {
    "content": {
      "title": "Title in Russian",
      "description": "Atmospheric text in Russian (2-3 sentences). Incorporate visual cues from surroundings (e.g., 'To the north, the massive gates loom...')."
    }
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

ChatMode = Literal["dungeon_generator", "item_description", "npc_dialogue", "batch_location_desc"]
