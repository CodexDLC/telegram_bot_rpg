# ⚔️ Hand Stats Modifiers

⬅️ [Назад](./README.md) | 🏠 [Документация](../../../../README.md)

Модификаторы для правой и левой руки (или двуручного хвата).

## MainHandStatsDTO (Правая рука)
*   **`main_hand_damage_base`**: Базовый урон.
    *   **Источник:** Item (Weapon).
*   **`main_hand_damage_spread`**: Разброс урона (0.1 = 10%).
    *   **Источник:** Item (Weapon). Сжимается навыком Weapon Mastery.
*   **`main_hand_damage_bonus`**: Дополнительный урон.
    *   **Источник:** Strength (только для Unarmed) или Item Affix.
*   **`main_hand_penetration`**: Пробивание брони.
    *   **Источник:** Strength (2%/pt) + Item Affix.
*   **`main_hand_accuracy`**: Точность.
    *   **Источник:** Item (Weapon). Штраф снимается навыком Weapon Mastery.
*   **`main_hand_crit_chance`**: Шанс крита.
    *   **Источник:** Item (Weapon Base) + Item Quality.

## OffHandStatsDTO (Левая рука / Щит)
*   **`off_hand_damage_base`**
*   **`off_hand_damage_spread`**
*   **`off_hand_damage_bonus`**
*   **`off_hand_penetration`**
*   **`off_hand_accuracy`**
*   **`off_hand_crit_chance`**
