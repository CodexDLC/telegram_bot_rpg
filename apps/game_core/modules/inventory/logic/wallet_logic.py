from apps.common.schemas_dto.inventory_dto import InventorySessionDTO


class WalletLogic:
    """
    Логика работы с кошельком и ресурсами.
    А также расчет вместимости инвентаря.
    """

    BASE_INVENTORY_SIZE = 20

    def get_summary(self, session: InventorySessionDTO) -> dict[str, int]:
        """
        Возвращает сводку для хедера инвентаря:
        - Текущий вес (кол-во предметов)
        - Макс вес
        - Баланс основных валют
        """
        current_weight = self._calculate_weight(session)
        max_weight = self._calculate_capacity(session)

        # Баланс (пыль, золото)
        dust = session.wallet.currency.get("currency_dust", 0)
        gold = session.wallet.currency.get("currency_gold", 0)

        return {"weight": current_weight, "max_weight": max_weight, "dust": dust, "gold": gold}

    def _calculate_weight(self, session: InventorySessionDTO) -> int:
        """Считает количество предметов в сумке (не надетых)."""
        return sum(1 for i in session.items.values() if i.location == "inventory")

    def _calculate_capacity(self, session: InventorySessionDTO) -> int:
        """
        Считает максимальную вместимость.
        База + Бонусы от экипировки.
        """
        bonus = 0
        # Пробегаем по надетым вещам и ищем бонусы
        for item in session.items.values():
            if item.location == "equipped" and item.data.bonuses:
                # Предполагаем, что бонусы лежат в item.data.bonuses
                # Ключ бонуса: 'inventory_slots_bonus'
                bonus += int(item.data.bonuses.get("inventory_slots_bonus", 0))

        return self.BASE_INVENTORY_SIZE + bonus

    def has_free_slots(self, session: InventorySessionDTO, amount: int = 1) -> bool:
        """Проверяет, есть ли место."""
        current = self._calculate_weight(session)
        max_cap = self._calculate_capacity(session)
        return (current + amount) <= max_cap
