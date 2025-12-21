import random
import re
from typing import Any

from loguru import logger as log
from simpleeval import SimpleEval


class ScenarioEvaluator:
    """
    Саппорт-класс для математических и логических вычислений сценария.
    Инкапсулирует логику SimpleEval и парсинг префиксной арифметики.
    """

    def __init__(self):
        # Инициализация движка SimpleEval
        self.s_eval = SimpleEval()

        # Регистрация безопасных функций для использования в формулах
        self.s_eval.functions = {"rand": random.randint, "min": min, "max": max, "abs": abs}

        # Регулярное выражение для поиска кубиков (напр., 1d6, 2d10)
        self.dice_pattern = re.compile(r"(\d+)d(\d+)")

    # --- Публичные методы (Интерфейс для Оркестратора) ---

    def check_condition(self, expression: str, context: dict[str, Any]) -> bool:
        """
        Проверяет логическое условие (напр., для Smart Selection).
        Пример выражения: "(p_str + p_agi) > 20 and p_has_key == 1"
        """
        if not expression or not isinstance(expression, str) or expression.strip() == "":
            return True

        # Подставляем переменные из контекста сессии
        self.s_eval.names = context
        try:
            # Вычисляем логическое значение
            result = self.s_eval.eval(expression)
            return bool(result)
        except (SyntaxError, NameError, TypeError, ValueError, AttributeError, LookupError, ArithmeticError) as e:
            log.error(f"Evaluator | action=check_condition status=failed expr='{expression}' error='{e}'")
            return False

    def apply_math(self, math_instructions: dict[str, str], context: dict[str, Any]) -> dict[str, Any]:
        """
        Применяет математические изменения к статам.
        Пример math_instructions: {"p_hp": "-10", "p_gold": "+1d50", "p_exp": "p_int * 1.5"}
        """
        new_context = context.copy()

        for var_name, instruction in math_instructions.items():
            if not isinstance(instruction, str):
                new_context[var_name] = instruction
                continue

            # 1. Сначала обрабатываем кубики, если они есть в строке
            processed_instr = self._process_dice(instruction)

            # 2. Получаем текущее значение переменной
            current_val = new_context.get(var_name, 0)

            # 3. Вычисляем финальное значение
            new_context[var_name] = self._calculate_step(current_val, processed_instr, new_context)

        return new_context

    # --- Внутренняя логика (Парсинг и вычисления) ---

    def _calculate_step(self, current_val: Any, instr: str, context: dict[str, Any]) -> Any:
        """
        Разбирает арифметические префиксы (+, -, =) или выполняет сложную формулу.
        """
        instr = instr.strip()

        try:
            # Арифметический префикс: Инкремент
            if instr.startswith("+"):
                delta = self._evaluate_fragment(instr[1:], context)
                return current_val + delta

            # Арифметический префикс: Декремент
            elif instr.startswith("-"):
                delta = self._evaluate_fragment(instr[1:], context)
                return current_val - delta

            # Арифметический префикс: Прямое присваивание
            elif instr.startswith("="):
                return self._evaluate_fragment(instr[1:], context)

            # Если префиксов нет, вычисляем как полноценную формулу через SimpleEval
            return self._evaluate_fragment(instr, context)

        except (SyntaxError, NameError, TypeError, ValueError, AttributeError, LookupError, ArithmeticError) as e:
            log.warning(f"Evaluator | action=calculate_step status=fallback instr='{instr}' error='{e}'")
            return self._to_numeric_if_possible(instr)

    def _evaluate_fragment(self, fragment: str, context: dict[str, Any]) -> Any:
        """Вычисляет фрагмент строки через SimpleEval или возвращает число."""
        self.s_eval.names = context
        try:
            return self.s_eval.eval(fragment)
        except (SyntaxError, NameError, TypeError, ValueError, AttributeError, LookupError, ArithmeticError):
            return self._to_numeric_if_possible(fragment)

    def _process_dice(self, text: str) -> str:
        """
        Находит все вхождения типа '1d6' и заменяет их на результат броска.
        Напр.: '2d10 + 5' -> '14 + 5' (если выпало 14)
        """

        def roll_replacer(match):
            count = int(match.group(1))
            sides = int(match.group(2))
            # Защита от безумных значений
            count = min(count, 100)
            sides = min(sides, 1000)
            result = sum(random.randint(1, sides) for _ in range(count))
            return str(result)

        return self.dice_pattern.sub(roll_replacer, text)

    def _to_numeric_if_possible(self, val: str) -> int | float | str:
        """Приводит строку к числу, если это возможно."""
        try:
            if "." in val:
                return float(val)
            return int(val)
        except ValueError:
            return val
