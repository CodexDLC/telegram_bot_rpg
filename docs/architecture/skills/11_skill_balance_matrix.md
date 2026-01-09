# Skill Balance Matrix & Progression Pacing

## 1. Stat Weight Philosophy (The "Sum 4" Rule)
Для предотвращения появления "God Stats" и обеспечения вариативности билдов, принята следующая система весов.

**Правило:** Сумма весов характеристик для любого навыка должна быть равна **4**.
**Тип данных:** Только целые числа (`int`).

### Допустимые конфигурации:
1.  **Triad:** `2 (Primary) + 1 (Secondary) + 1 (Tertiary)`.
2.  **Dual:** `2 + 2`.
3.  **Bias:** `3 + 1`.

---

## 2. Stat Distribution Matrix (Full List)

### A. Combat (Weapon Mastery)
| Skill | Weights (Sum 4) | Rationale |
| :--- | :--- | :--- |
| **Swords** | STR (2) + AGI (1) + END (1) | Сила - основа. Ловкость и Выносливость - поддержка. |
| **Fencing** | AGI (2) + PER (1) + STR (1) | Скорость и точность в приоритете. |
| **Polearms** | STR (2) + AGI (1) + PER (1) | Сила удержания. Ловкость и Глазомер для дистанции. |
| **Macing** | STR (2) + END (1) + MEN (1) | Грубая сила. Стойкость и Ярость (Men). |
| **Archery** | AGI (2) + PER (1) + STR (1) | Координация. Глазомер и Сила натяжения. |
| **Unarmed** | AGI (2) + STR (1) + END (1) | Техника (Agi). Ударная мощь и Набивка. |

### B. Combat (Tactical Styles)
| Skill | Weights (Sum 4) | Rationale |
| :--- | :--- | :--- |
| **One Handed** | AGI (2) + PER (1) + STR (1) | Баланс одной руки. |
| **Two Handed** | STR (2) + END (1) + AGI (1) | Сила хвата и инерция. |
| **Shield** | STR (2) + END (1) + AGI (1) | Сила блока важнее всего. |
| **Dual Wield** | AGI (2) + PER (1) + STR (1) | Координация двух рук. |

### C. Combat (Armor Proficiency)
| Skill | Weights (Sum 4) | Rationale |
| :--- | :--- | :--- |
| **Heavy Armor** | STR (2) + END (2) | Равнозначные: носить вес и держать удар. |
| **Light Armor** | AGI (2) + END (1) + PER (1) | Уворот. Выносливость для бега. |
| **Medium Armor** | END (2) + STR (1) + AGI (1) | Выносливость - основа баланса. |

### D. Combat Support
| Skill | Weights (Sum 4) | Rationale |
| :--- | :--- | :--- |
| **Parrying** | AGI (2) + PER (1) + STR (1) | Реакция (Agi) главная. |
| **Tactics** | INT (2) + MEM (2) | Интеллект и Память. Сложность тактических схем. |
| **Anatomy** | INT (2) + PER (2) | Знание и Наблюдение равнозначны. |
| **First Aid** | MEM (2) + INT (1) + AGI (1) | Память (опыт) важнее теории. Ловкость рук. |

### E. Crafting
| Skill | Weights (Sum 4) | Rationale |
| :--- | :--- | :--- |
| **Alchemy** | INT (2) + MEM (1) + PRED (1) | Наука. Память и Предвидение (Luck). |
| **Weapon Craft** | STR (2) + AGI (1) + PER (1) | Сила ковки. Точность формы. |
| **Armor Craft** | STR (2) + END (2) | Тяжелая работа с металлом. |
| **Jewelry** | AGI (2) + PER (1) + PRED (1) | Тонкая моторика. |
| **Artifacts** | MEN (2) + INT (1) + MEM (1) | Сила воли/магии (Men) - основа артефактов. |

### F. Gathering
| Skill | Weights (Sum 4) | Rationale |
| :--- | :--- | :--- |
| **Mining** | STR (2) + END (2) | Тяжелый труд. |
| **Herbalism** | PER (2) + MEM (1) + INT (1) | Поиск (Per) главный. |
| **Skinning** | AGI (2) + PER (1) + END (1) | Ловкость рук. |
| **Woodcutting** | STR (2) + END (2) | Сила и выносливость. |
| **Hunting** | PER (2) + AGI (1) + END (1) | Поиск дичи и преследование. |
| **Archaeology** | PER (2) + MEM (1) + INT (1) | Поиск и знания. |
| **Gathering** | PER (2) + END (2) | Внимательность и выносливость. |

### G. Survival
| Skill | Weights (Sum 4) | Rationale |
| :--- | :--- | :--- |
| **Scouting** | PER (2) + MEM (1) + AGI (1) | Заметить (Per) главное. |
| **Taming** | PROJ (2) + MEM (1) + MEN (1) | Проекция (Харизма) главная. |
| **Adaptation** | END (2) + MEN (2) | Тело и Дух. |

### H. Trade (Mercantile)
| Skill | Weights (Sum 4) | Rationale |
| :--- | :--- | :--- |
| **Accounting** | INT (2) + PRED (2) | Точность и Предвидение (Luck) в цифрах. |
| **Brokerage** | PROJ (2) + PRED (1) + INT (1) | Убеждение. |
| **Contracts** | INT (2) + PROJ (1) + PRED (1) | Юридическая точность. |
| **Trade Relations** | PROJ (2) + PRED (2) | Связи и Предвидение. |

### I. Social (Leadership)
| Skill | Weights (Sum 4) | Rationale |
| :--- | :--- | :--- |
| **Leadership** | PROJ (2) + MEN (1) + MEM (1) | Проекция (Харизма) лидера. |
| **Organization** | INT (2) + PROJ (1) + MEM (1) | Структура. |
| **Team Spirit** | PROJ (2) + MEN (1) + PRED (1) | Мораль. |
| **Egoism** | MEN (2) + PRED (2) | Самолюбие и Предвидение. |

---

## 3. Progression Pacing (Rate Modifiers)
*Без изменений.*
