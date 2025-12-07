# Technical Design Doc #4: UI Service & Overlay Composition

**Версия:** 1.0 **Дата:** 06.12.2025 **Слой:** UI Service Layer (Middleware) **Суть:** Сборка данных для клиента. Агрегация статики, динамики и интерфейсных флагов.

## 1. Архитектура UI Service

Этот слой выступает фасадом для фронтенда. Он содержит публичные методы для Handlers.

- **Input:** Запрос от Handler (`get_location_view(x, y)`).
    
- **Process:** Оркестрация вызовов к Game Services.
    
- **Output:** Готовый ViewModel (JSON) для отрисовки Unity/Web.
    

## 2. Композиция Данных (Data Aggregation)

UI Service делает три параллельных запроса (или последовательных с кешированием).

### 2.1 Сборка Слоев

1. **Base Layer (Atmosphere):**
    
    - _Call:_ `WorldGridService.getContent(x, y)`
        
    - _Result:_ Текст от LLM ("Ночной лес...").
        
2. **Object Layer (Interactive):**
    
    - _Check:_ Есть ли `service_object_key`?
        
    - _Logic:_ Если ключа нет в таблице активных объектов (Lazy Load) -> UI Service инициирует создание дефолтного состояния ("Вход закрыт").
        
    - _Result:_ Добавочный текст/кнопка ("Войти в Разлом").
        
3. **Threat Layer (UI Flags):**
    
    - _Call:_ `ThreatService.getThreatLevel(x, y)` (Doc #2).
        
    - _Logic:_
        
        - Если рядом Global Rift -> `THREAT_HIGH` -> Красный UI.
            
        - Если это Quest Instance -> `THREAT_SAFE` (или Local Danger) -> Обычный UI.
            

## 3. Итоговый Ответ (Response DTO)

То, что улетает на клиент.

JSON

```
{
  "view_mode": "EXPLORATION",
  "narrative": {
    "main_text": "Ночной лес... [Текст LLM]",
    "object_text": "Перед вами мерцающий проход."
  },
  "ui_config": {
    "theme": "DEFAULT", // Не меняем на RED, так как рифт временный
    "scan_available": true
  },
  "actions": [
    {"id": "enter_rift", "label": "Шагнуть в разлом", "req": "quest_active"}
  ]
}
```