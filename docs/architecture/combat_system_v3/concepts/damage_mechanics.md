# ⚔️ Damage Mechanics (RBC v3.1)

⬅️ [Назад](./README.md)

> **Status:** Draft / Auto-Generated from Code
> **Source:** `CombatResolver.py`

В этом документе описаны формулы расчета, используемые в боевом движке.

## 1. Pipeline Steps (Порядок расчета)

Расчет происходит последовательно. Каждый шаг может прервать цепочку (вернуть 0 урона).

1.  **Accuracy Check** (Попадание)
2.  **Crit / Trigger Roll** (Определение крита и спецэффектов)
3.  **Evasion Check** (Уклонение)
4.  **Parry Check** (Парирование оружием)
5.  **Block Check** (Блок щитом)
6.  **Damage Calculation** (Расчет цифр)

---

## 2. Formulas (Формулы)

### A. Accuracy (Точность)
Базовая проверка на попадание.
*   **Formula:** `FinalAcc = BaseAcc * Multiplier`
*   **Check:** `Random(0..1) < FinalAcc`
*   **Result:** Если провал -> `is_miss=True`, урон 0.

### B. Evasion (Уклонение)
Шанс избежать урона полностью.
*   **Formula:** `Chance = (DodgeChance - AntiDodge)`.
*   **Cap:** Ограничено `dodge_cap`.
*   **Modifiers:**
    *   `evasion_halved`: Шанс делится на 2 (например, при атаке со спины).
    *   `ignore_evasion_cap`: Игнорирование капа.
*   **Result:** Если успех -> `is_dodged=True`, урон 0. Возможна контратака.

### C. Parry (Парирование)
Шанс отбить удар оружием.
*   **Formula:** `Chance = ParryChance`.
*   **Cap:** Ограничено `parry_cap`.
*   **Result:** Если успех -> `is_parried=True`. Урон 0 (или снижен). Возможна контратака.

### D. Block (Блок щитом)
Шанс принять удар на щит.
*   **Formula:** `Chance = ShieldBlockChance`.
*   **Cap:** Ограничено `shield_block_cap`.
*   **Result:**
    *   **Full Block:** Если успех -> `is_blocked=True`, урон 0.
    *   **Partial Absorb:** Если провал, но сработал `shield_reflect` -> Поглощение 40% урона + Отражение.

---

## 3. Damage Calculation (Расчет Урона)

Если все проверки пройдены, считается итоговый урон.

### Step 1: Base Damage
*   `Base = WeaponDamage + PhysicalBonus`
*   `RawDamage = Random(Base * (1-Spread), Base * (1+Spread))`

### Step 2: Critical Multiplier
Если `is_crit=True`:
*   **Magic:** `x3.0` (Фиксировано).
*   **Physical:** `x1.0` (По умолчанию крит не дает урона, только триггеры).
    *   *Exception:* Если есть флаг `crit_damage_boost`, множитель берется из оружия.

### Step 3: Mitigation (Снижение)

#### Physical Damage
1.  **Resist:** `Mitigation = PhysResist - Penetration`.
2.  **Apply:** `Dmg = Dmg * (1.0 - Mitigation)`.
3.  **Flat Armor:** `Dmg = Dmg - FlatArmor`.
4.  **Heavy Armor vs Crit:** Если цель в тяжелой броне и прошел крит -> Снижение урона на `SkillLevel * 20%`.

#### Elemental Damage
1.  **Resist:** `Mitigation = ElemResist - MagicPenetration`.
2.  **Apply:** `Dmg = Dmg * (1.0 - Mitigation)`.

### Step 4: Special Modifiers
*   **Multi-Hit Penalty:** Если это 2-й или 3-й удар в серии -> Урон снижается (Heavy Armor Mastery усиливает штраф).
*   **Reflect:** Если сработал `partial_absorb` -> 40% урона возвращается атакующему.

---

## 4. Triggers (Триггеры)
Система событий, меняющая ход расчета.

*   **ON_HIT:** Срабатывает при попадании. Может включить комбо.
*   **ON_DODGE:** Срабатывает при увороте. Может включить контратаку.
*   **ON_CRIT:** Срабатывает при крите.

> *Примечание: Логика триггеров задается в `TRIGGER_RULES` и может меняться динамически.*
