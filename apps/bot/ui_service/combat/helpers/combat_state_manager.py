from typing import Any

from aiogram.fsm.context import FSMContext

# Ключ для хранения временных данных боя (Draft)
KEY_COMBAT_DRAFT = "combat_draft_data"


class CombatStateManager:
    """
    Управляет временным состоянием (Draft) боя в FSM.
    Реализует логику "Один слот - Одно значение" (Radio Button) для каждой колонки (layer).
    """

    def __init__(self, state: FSMContext):
        self.state = state

    async def get_payload(self) -> dict[str, Any]:
        """
        Возвращает полный слепок драфта.
        Пример: {'atk_main': 'head', 'atk_off': 'legs', 'def': 'chest_belly', 'ability_id': 'fireball'}
        """
        data = await self.state.get_data()
        return data.get(KEY_COMBAT_DRAFT, {})

    async def clear_draft(self) -> None:
        """
        Очищает черновик (после отправки хода или выхода).
        """
        await self.state.update_data({KEY_COMBAT_DRAFT: {}})

    # --- Зоны (Attack/Block) ---

    async def toggle_zone(self, layer: str, zone_id: str) -> dict[str, Any]:
        """
        Переключает зону в указанном слое (atk_main, atk_off, def).
        В одном слое может быть только одна выбранная зона.
        """
        draft = await self.get_payload()

        # Получаем текущую выбранную зону в этом слое (строка или None)
        current_zone = draft.get(layer)

        if current_zone == zone_id:
            # Если кликнули по уже выбранной -> снимаем выбор
            draft.pop(layer, None)
        else:
            # Если кликнули по новой -> заменяем (Radio Button)
            draft[layer] = zone_id

        await self._save(draft)
        return draft

    # --- Способности (Skills) ---

    async def set_ability(self, ability_id: str | None) -> dict[str, Any]:
        """
        Устанавливает или сбрасывает выбранную способность.
        Тоже работает как Radio Button (одна способность за раз).
        """
        draft = await self.get_payload()

        # Если кликнули на ту же самую способность -> отмена
        if ability_id and draft.get("ability_id") == ability_id:
            draft.pop("ability_id", None)
        elif ability_id:
            draft["ability_id"] = ability_id
        else:
            draft.pop("ability_id", None)

        await self._save(draft)
        return draft

    # --- Цели (Target) ---

    async def set_target(self, target_id: int) -> None:
        """
        Запоминает текущую цель атаки.
        """
        draft = await self.get_payload()
        draft["target_id"] = target_id
        await self._save(draft)

    async def get_target(self) -> int | None:
        draft = await self.get_payload()
        val = draft.get("target_id")
        return int(val) if val is not None else None

    # --- Export ---

    async def get_move_data(self) -> dict[str, Any]:
        """
        Собирает данные драфта в формат, готовый для отправки в Core (CombatMoveDTO).
        """
        draft = await self.get_payload()

        # Собираем зоны атаки (Main + Off)
        attack_zones = []
        if "atk_main" in draft:
            attack_zones.append(draft["atk_main"])
        if "atk_off" in draft:
            attack_zones.append(draft["atk_off"])

        # Собираем зоны блока
        block_zones = []
        if "def" in draft:
            block_zones.append(draft["def"])

        return {"attack_zones": attack_zones, "block_zones": block_zones, "ability_key": draft.get("ability_id")}

    # --- Helpers ---

    async def _save(self, draft_data: dict[str, Any]) -> None:
        await self.state.update_data({KEY_COMBAT_DRAFT: draft_data})
