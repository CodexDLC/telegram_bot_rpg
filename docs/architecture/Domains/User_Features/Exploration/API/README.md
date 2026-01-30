# 🔌 Exploration API

## Gateway Methods

Все методы возвращают объект `CoreResponseDTO`.
Ниже указан тип данных (Payload), который лежит внутри `CoreResponseDTO.data`.

### 1. `move(char_id: int, direction: str)`
Перемещение персонажа.
*   **Returns:** `CoreResponseDTO[WorldNavigationDTO | EncounterDTO]`
    *   *Success:* Возвращает `WorldNavigationDTO` (новая локация).
    *   *Interrupted:* Возвращает `EncounterDTO` (если случилось событие).

### 2. `look_around(char_id: int)`
Обновление данных локации.
*   **Returns:** `CoreResponseDTO[WorldNavigationDTO]`
    *   Всегда возвращает актуальное состояние текущей локации.

### 3. `interact(char_id: int, target_id: str, action: str)`
Взаимодействие с объектом.
*   **Returns:** `CoreResponseDTO[InteractionResponse]`
    *   `InteractionResponse` может содержать текст диалога, лут или результат действия.

### 4. `use_service(char_id: int, service_id: str)`
Вход в сервис (смена режима).
*   **Returns:** `CoreResponseDTO[RedirectResponse]`
    *   Содержит инструкцию для клиента переключить UI на другой домен (например, `Arena`).
