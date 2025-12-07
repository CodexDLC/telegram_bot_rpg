# [FINAL] Technical Design Doc #2: The Threat System (Field Theory)

Версия: 3.1 (Rainbow Corners)

Суть: Расчет опасности на основе наложения полей. Углы карты — зоны максимальной энтропии.

### 1. Источники Полей (Emitters)

|**Тип**|**Координаты**|**Power (Сила)**|**Falloff (Затухание)**|**Эффект**|
|---|---|---|---|---|
|**PORTAL (Hub)**|`D4` Center `[52:52]`|**-2.0**|**0.04** (Медленное)|**Stabilizer.** Давит угрозу в центре карты.|
|**ANCHORS (Roots)**|`A4, G4, D1, D7`|**+1.2**|**0.08** (Среднее)|**Source.** Генерируют чистую стихию (Tier 5).|

_(Дополнительные мелкие данжи C3, E5 пока не считаем источниками поля, чтобы не шуметь, они просто POI)._

### 2. Топология Опасности (Threat Map)

В результате наложения полей (`Sum(Anchors) + Portal`) получается такая картина:

1. **Центр (D4):** Влияние Портала (-2.0) перекрывает всё. **Tier 0 (Safe)**.
    
2. **Ближний круг (C3, C5...):** Портал слабеет, Якоря еще далеко. **Tier 2-3**.
    
3. **Кресты (A4, D1...):** Эпицентры Якорей. Максимальная _чистая_ сила. **Tier 5 (Pure)**.
    
4. **УГЛЫ (A1, A7...):**
    
    - Портал почти не действует (очень далеко).
        
    - Влияние ДВУХ Якорей накладывается друг на друга (Сумма полей).
        
    - **Результат:** `1.2 + 1.2 = Overload`. Это **Tier 7 (Rainbow)**.
        

---

### 3. Техническая реализация (Calculator)

Метод `ThreatService.calculate_threat(x, y)`:

Python

```
def calculate_threat(x, y):
    # 1. Negative Field (Portal)
    dist_hub = get_dist(x, y, HUB_X, HUB_Y)
    stability = 2.0 / (1 + dist_hub * 0.04)

    # 2. Positive Fields (Anchors)
    danger = 0.0
    for anchor in ANCHORS:
        dist = get_dist(x, y, anchor.x, anchor.y)
        # Суммируем влияние всех якорей
        danger += 1.2 / (1 + dist * 0.08)

    # 3. Result
    total = danger - stability
    return clamp(total, 0.0, 1.0)
```

**Результат маппинга:**

- `0.0 - 0.1` -> Safe Zone (Город)
    
- ...
    
- `0.8 - 0.9` -> Tier 5 (Якоря)
    
- `0.95 - 1.0` -> Tier 7 (Углы)