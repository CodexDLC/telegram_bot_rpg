# 🔥 Elemental & Status Modifiers

⬅️ [Назад](./README.md) | 🏠 [Документация](../../../../README.md)

Модификаторы стихий и статусных эффектов.

## ElementalStatsDTO (Energy-Resistances)
*   **Источник (Base):** `Mental` (2%/pt).
*   **Множитель:** Навык `Adaptation` (до x3).

Для каждой стихии (Fire, Water, Air, Earth, Light, Dark, Arcane, Nature):
*   **`{element}_damage_bonus`**: Бонус к урону стихией.
*   **`{element}_resistance`**: Сопротивление стихии.

## StatusStatsDTO (Bio & Control)

### Control (Mental Base)
*   **Источник (Base):** `Mental` (2%/pt).
*   **Множитель:** Навык `Adaptation` (до x3).
*   **`control_chance_bonus`**: Шанс наложить контроль (Stun, Root).
*   **`control_resistance`**: Сопротивление контролю.
*   **`mental_resistance`**: Сопротивление ментальным атакам (Fear, Sleep).
*   **`debuff_avoidance`**: Шанс избежать наложения дебаффа.
*   **`shock_resistance`**: Сопротивление шоку.

### Bio (Endurance Base)
*   **Источник (Base):** `Endurance` (2%/pt).
*   **Множитель:** Навык `Adaptation` (до x3).
*   **`poison_damage_bonus`**: Урон ядом.
*   **`poison_resistance`**: Сопротивление яду.
*   **`poison_efficiency`**: Эффективность ядов.
    *   **Источник (Base):** `Projection` (Debuff Efficiency).
    *   **Множитель:** Навык `Alchemy`.
*   **`bleed_damage_bonus`**: Урон кровотечением.
    *   **Источник (Base):** `Strength` (Physical Penetration).
    *   **Множитель:** Навык `Weapon Mastery`.
*   **`bleed_resistance`**: Сопротивление кровотечению.
