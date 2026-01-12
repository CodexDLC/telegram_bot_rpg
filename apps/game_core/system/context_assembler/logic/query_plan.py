"""
Модуль определяет планы запросов (Query Plans) для разных scope.
"""

QUERY_PLANS = {
    "combats": ["attributes", "inventory", "skills", "vitals", "symbiote"],
    "status": ["attributes", "vitals", "symbiote"],
    "inventory": ["inventory", "wallet"],
    # Будущие scope (закомментировать до реализации):
    # "exploration": ["attributes", "skills", "vitals"],
    # "trade": ["attributes", "inventory", "wallet"],
    # "tutorial": ["attributes", "vitals"],
}


def get_query_plan(scope: str) -> list[str]:
    """
    Возвращает список таблиц для загрузки на основе scope.
    По умолчанию возвращает план для 'combats' (максимальный набор).

    Raises:
        ValueError: Если scope не поддерживается.
    """
    if scope not in QUERY_PLANS:
        raise ValueError(f"Unsupported scope: {scope}. Available scopes: {list(QUERY_PLANS.keys())}")

    return QUERY_PLANS[scope]
