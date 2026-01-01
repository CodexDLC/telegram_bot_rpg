from typing import Any

from loguru import logger
from simpleeval import simple_eval

from apps.game_core.resources.game_data.stats_formulas import MODIFIER_RULES


class StatsWaterfallCalculator:
    """
    Универсальный калькулятор характеристик (Waterfall Calculation).

    Логика расчета:
    1. Атрибуты (Stats): Складываются все источники (Base + Buffs - Debuffs).
    2. База Модификаторов (Base Modifiers):
       - Конвертация Атрибутов (Bridge) -> дает Flat (+).
       - Скиллы/Врожденное -> дает Flat (+).
       - Флэтовые бонусы предметов (Урон оружия) -> дает Flat (+).
    3. Финальные Модификаторы:
       - База умножается на все мультипликаторы (Items, Buffs, Abilities).
       - Формула: Final = (Sum(Flats)) * Product(Multipliers).
    """

    # Кеш для трансформированных правил (Source -> [Target, Factor])
    _SOURCE_TO_TARGET_RULES: dict[str, list[dict[str, Any]]] = {}

    @classmethod
    def _get_rules(cls) -> dict[str, list[dict[str, Any]]]:
        """
        Ленивая инициализация и трансформация правил из MODIFIER_RULES.
        Превращает {Target: {Source: Factor}} в {Source: [{Target, Factor}]}.
        """
        if not cls._SOURCE_TO_TARGET_RULES:
            transformed: dict[str, list[dict[str, Any]]] = {}
            for target_mod, sources in MODIFIER_RULES.items():
                for source_attr, factor in sources.items():
                    if source_attr not in transformed:
                        transformed[source_attr] = []
                    transformed[source_attr].append({"target": target_mod, "factor": factor})
            cls._SOURCE_TO_TARGET_RULES = transformed
        return cls._SOURCE_TO_TARGET_RULES

    @staticmethod
    def calculate_waterfall(raw_data: dict[str, Any]) -> tuple[dict[str, float], dict[str, str]]:
        """
        Полный цикл расчета характеристик.

        Args:
            raw_data: Структура v:raw (attributes, modifiers).

        Returns:
            Tuple: (v:cache (values), v:explanation (formulas))
        """
        # 1. Расчет Атрибутов (Primary Stats)
        # Атрибуты всегда аддитивные.
        raw_attributes = raw_data.get("attributes", {})
        final_attributes, attr_explanations = StatsWaterfallCalculator._calculate_attributes(raw_attributes)

        # 2. Конвертация (Derivation Bridge)
        # Генерируем бонусы к модификаторам на основе атрибутов.
        derived_bonuses = StatsWaterfallCalculator._derive_bonuses(final_attributes)

        # 3. Расчет Модификаторов (Secondary Stats)
        # Смешиваем Derived (Base) + Raw Modifiers (Skills, Items, Buffs).
        raw_modifiers = raw_data.get("modifiers", {})
        final_modifiers, mod_explanations = StatsWaterfallCalculator._calculate_modifiers(
            raw_modifiers, derived_bonuses
        )

        # Объединяем все в плоские словари
        cache_result = {**final_attributes, **final_modifiers}
        explanation_result = {**attr_explanations, **mod_explanations}

        return cache_result, explanation_result

    @staticmethod
    def _calculate_attributes(raw_attributes: dict[str, Any]) -> tuple[dict[str, float], dict[str, str]]:
        """
        Фаза 1: Расчет атрибутов.
        Простое сложение всех значений (Base + Flats).
        """
        results = {}
        explanations = {}

        for attr_name, data in raw_attributes.items():
            # Base
            base_raw = data.get("base", 0.0)
            base = float(base_raw) if base_raw else 0.0

            # Flats (Buffs, Debuffs, Traits)
            flats_sum = 0.0

            # Обрабатываем flats
            for _source, val_str in data.get("flats", {}).items():
                flats_sum += StatsWaterfallCalculator._parse_simple_value(str(val_str))

            for _source, val_str in data.get("percents", {}).items():
                flats_sum += StatsWaterfallCalculator._parse_simple_value(str(val_str))

            final_val = base + flats_sum
            results[attr_name] = final_val
            explanations[attr_name] = f"{base} + {flats_sum}"  # Упрощенная формула для атрибутов

        return results, explanations

    @staticmethod
    def _derive_bonuses(attributes: dict[str, float]) -> dict[str, list[str]]:
        """
        Фаза 2: Генерация бонусов от атрибутов (Bridge).
        Использует MODIFIER_RULES из stats_formulas.py.
        Возвращает словарь: { "modifier_name": ["+Value", ...] }
        """
        derived: dict[str, list[str]] = {}
        rules_map = StatsWaterfallCalculator._get_rules()

        for attr_name, attr_value in attributes.items():
            rules = rules_map.get(attr_name, [])
            for rule in rules:
                target = rule["target"]
                factor = rule["factor"]

                # Расчет бонуса (Base * Factor)
                bonus_val = attr_value * factor

                if bonus_val != 0:
                    if target not in derived:
                        derived[target] = []
                    # Записываем как Flat Add ("+X")
                    # Это станет частью Базы модификатора
                    cmd = f"+{bonus_val}"
                    derived[target].append(cmd)

        return derived

    @staticmethod
    def _calculate_modifiers(
        raw_modifiers: dict[str, Any], derived_bonuses: dict[str, list[str]]
    ) -> tuple[dict[str, float], dict[str, str]]:
        """
        Фаза 3: Расчет модификаторов.
        Формула: (Sum(Flats/Base)) * Product(Multipliers).
        """
        results_values = {}
        results_explanations = {}

        # Собираем все ключи
        all_keys = set(raw_modifiers.keys()) | set(derived_bonuses.keys())

        for mod_name in all_keys:
            sources = []

            # 1. Добавляем Derived (это База от статов)
            if mod_name in derived_bonuses:
                sources.extend(derived_bonuses[mod_name])

            # 2. Добавляем Raw (Скиллы, Предметы, Баффы)
            if mod_name in raw_modifiers:
                raw_data_entry = raw_modifiers[mod_name]
                # Может быть структура {"sources": {...}} или сразу dict
                raw_sources = raw_data_entry.get("sources", {}) if isinstance(raw_data_entry, dict) else {}

                if isinstance(raw_sources, dict):
                    sources.extend([str(v) for v in raw_sources.values()])
                elif isinstance(raw_sources, list):
                    sources.extend([str(v) for v in raw_sources])

            # 3. Расчет
            final_val, explanation = StatsWaterfallCalculator._evaluate_pipeline(sources)
            results_values[mod_name] = final_val
            results_explanations[mod_name] = explanation

        return results_values, results_explanations

    @staticmethod
    def _evaluate_pipeline(commands: list[str], base_value: float = 0.0) -> tuple[float, str]:
        """
        Вычисляет значение, собирая строковую формулу и выполняя её через simpleeval.
        """
        flats = [str(base_value)] if base_value != 0 else []
        mults = []

        for cmd in commands:
            if not cmd:
                continue
            operator = cmd[0]
            val_str = cmd[1:]

            if operator == "=":
                # Override полностью сбрасывает строку базы
                flats = [val_str]
            elif operator == "+":
                flats.append(val_str)
            elif operator == "-":
                flats.append(f"-{val_str}")
            elif operator == "*":
                mults.append(val_str)
            # Fallback для чисел без оператора (считаем как +)
            elif cmd.replace(".", "", 1).isdigit():
                flats.append(cmd)

        # 1. Сборка СТРОКИ (Explanation)
        # Собираем базу в скобки и умножаем на всё остальное
        base_expr = f"({' + '.join(flats)})" if flats else "0"
        mult_expr = f" * {' * '.join(mults)}" if mults else ""
        full_expression = f"{base_expr}{mult_expr}"

        # 2. Вычисление ЧИСЛА (Cache) через SimpleEval
        try:
            raw_result = simple_eval(full_expression)
            final_value = round(float(raw_result), 4)
        except Exception as e:  # noqa: BLE001
            logger.error(f"StatsWaterfallCalculator | Eval error: {e} expr='{full_expression}'")
            final_value = 0.0

        return final_value, full_expression

    @staticmethod
    def _parse_simple_value(val_str: str) -> float:
        """Парсит простое значение (+10, -5). Игнорирует * и =."""
        try:
            clean_val = val_str.replace("+", "")
            if "*" in clean_val or "=" in clean_val:
                return 0.0
            return float(clean_val)
        except ValueError:
            return 0.0
