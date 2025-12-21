from typing import Any

from loguru import logger as log


class ScenarioDirector:
    """
    Саппорт-класс для управления логикой переходов.
    Реализует Smart Selection и Branching на основе условий.
    """

    def __init__(self, evaluator):
        # Директор всегда работает в паре с Математиком
        self.evaluator = evaluator

    # --- 1. Smart Selection (Выбор из пула нод) ---

    def select_node_from_pool(self, candidate_nodes: list[dict[str, Any]], context: dict[str, Any]) -> str | None:
        """
        Проходит по списку потенциальных нод и выбирает ту,
        чьи требования (selection_requirements) подходят под статы игрока.
        """
        valid_nodes = []

        for node in candidate_nodes:
            # Берем условия входа в ноду из JSON
            requirements = node.get("selection_requirements")

            # Если требований нет или они пройдены — нода подходит
            if not requirements or self.evaluator.check_condition(requirements, context):
                valid_nodes.append(node)

        if not valid_nodes:
            log.warning(f"Director | action=smart_selection status=no_candidates context_keys={list(context.keys())}")
            return None

        # Приоритезация: выбираем самую "сложную" ноду (где больше всего условий)
        # или просто последнюю подходящую для гибкости
        selected_node = valid_nodes[-1]
        log.debug(f"Director | action=smart_selection status=success selected='{selected_node.get('node_key')}'")

        return str(selected_node.get("node_key"))

    # --- 2. Branching (Ветвление внутри действия) ---

    def resolve_branching(self, branching_logic: list[dict[str, Any]], context: dict[str, Any]) -> str:
        """
        Определяет финальную цель перехода после применения математики.
        Используется, когда у одной кнопки может быть несколько исходов (успех/провал).
        """
        # branching_logic — это список условий и веток перехода
        # Пример: [{"condition": "p_hp > 0", "to_node": "victory"}, {"condition": "default", "to_node": "death"}]

        for branch in branching_logic:
            condition = branch.get("condition")
            target_node = branch.get("to_node")

            # Ветка по умолчанию (если остальные не подошли)
            if condition == "default" or not condition:
                return str(target_node)

            # Проверяем условие ветки через Evaluator
            if self.evaluator.check_condition(condition, context):
                log.debug(
                    f"Director | action=branching status=branch_selected node='{target_node}' condition='{condition}'"
                )
                return str(target_node)

        return "error_node"  # Заглушка на случай полной ошибки логики

    # --- 3. Получение доступных действий ---

    def get_available_actions(self, actions_logic: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Фильтрует список кнопок в ноде, скрывая те, для которых не выполнены условия (Conditions).
        """
        available_actions = []

        for action_id, action_data in actions_logic.items():
            # Уровень 1: Проверка доступности самой кнопки
            condition = action_data.get("condition")

            if not condition or self.evaluator.check_condition(condition, context):
                available_actions.append(
                    {
                        "action_id": action_id,
                        "label": action_data.get("label", "Далее"),
                        "payload": action_data,  # Передаем данные для дальнейшей обработки в step
                    }
                )

        return available_actions
