




DUNGEON_JSON_SCHEMA_PROMPT = """

Твой ответ — СТРОГО один JSON-объект без каких-либо пояснений или текста вне JSON. Никакого Markdown. Только JSON на русском языке.

Схема JSON: { "dungeon_meta": { "name": str (Название локации), 
"theme": str (тема на англ., одно слово, e.g. "cave", "forest") }, 
"start_room_id": str (ID стартовой комнаты, должен быть ключом в "rooms"), 
"rooms": { "ID_комнаты": { "name": str (название комнаты), 
"level": int (номер уровня/этажа, e.g. 1), 
"description": list[str] (массив строк-абзацев), 
"exits": dict[str, str] (объект, e.g. {"Север": "room_2"}. Значение - ID комнаты из "rooms"), 
"event_potential": str (флаг для движка: "encounter", "loot", "trap" или "none") } } }

Ключевые требования:

1. Все ID в "exits" должны существовать как ключи в "rooms".
    
2. Локация должна быть связной (все комнаты доступны).
    
3. "rooms" - это ОБЪЕКТ (словарь), а не массив.
    
4. Стартовая комната (`start_room_id`) всегда должна иметь `"event_potential": "none"`.
    
5. Комната может иметь только один тип `event_potential`.

"""