# Combat Context Builder Specification (RBC v3.1)

## 1. Назначение
**Context Builder** — это фабрика, которая создает `PipelineContextDTO`.
Она принимает Интент, Статы и **External Modifiers** (результат Pre-Check в Executor).

---

## 2. Входные Данные
```python
def build_context(actor, intent, external_mods: dict = None) -> PipelineContextDTO:
```

## 3. Структура PipelineContextDTO

```python
class PipelineContextDTO:
    # A. Управление Фазами (Phase Control)
    # Определяет, какие части пайплайна будут запущены.
    phases: dict = {
        "run_pre_calc": True,   # Проверка условий
        "run_calculator": True, # Расчет урона/защиты
        "run_post_calc": True   # Применение эффектов/статусов
    }

    # B. Флаги и Формулы (для Калькулятора)
    stages: dict = {...}      # check_evasion, etc.
    calc_flags: dict = {...}  # force_crit, etc.
    formulas: dict = {...}    # evasion_algo, etc.

    # C. Триггеры (для AbilityService)
    pre_triggers: list = []
    post_triggers: list = []
```

---

## 4. Логика Сборки (Assembly Flow)

### Шаг 1: Применение External Modifiers (Interference)
Это самый высокий приоритет. Модификаторы могут отключить фазы.

*   Если `external_mods` содержит `disable_attack=True`:
    *   `phases["run_pre_calc"] = False`
    *   `phases["run_calculator"] = False`
    *   `phases["run_post_calc"] = True` (Оставляем, чтобы снять старые дебаффы или обновить кулдауны).
    *   **Итог:** Игрок не бьет, финт не срабатывает.

*   Если `external_mods` содержит `force_miss=True`:
    *   `calc_flags["force_hit"] = False`
    *   `stages["check_accuracy"] = False` (Авто-промах).

### Шаг 2: Анализ Актера и Интента
Выполняется только если `phases["run_calculator"] == True`.
Если атака отключена, нет смысла парсить финты и статы оружия (экономия ресурсов).

---

## 5. Валидация
Если атака отключена модификатором, валидация токенов пропускается (токены могут сгореть или сохраниться, в зависимости от геймдизайна).
