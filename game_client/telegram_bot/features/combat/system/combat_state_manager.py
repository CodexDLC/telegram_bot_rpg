from typing import Any

from aiogram.fsm.context import FSMContext

# Ключ для хранения временных данных боя (Draft)
KEY_COMBAT_DRAFT = "combat_draft_data"


class CombatStateManager:
    """
    Управляет временным состоянием (Draft) боя в FSM.
    v2.0: Поддержка финтов (Feints) вместо зон.
    """

    def __init__(self, state: FSMContext):
        self.state = state

    async def get_payload(self) -> dict[str, Any]:
        """
        Возвращает полный слепок драфта.
        Пример: {'feint_id': 'sand_throw', 'target_id': 123, 'ability_id': 'fireball'}
        """
        data = await self.state.get_data()
        return data.get(KEY_COMBAT_DRAFT, {})

    async def clear_draft(self) -> None:
        """
        Очищает черновик (после отправки хода или выхода).
        """
        await self.state.update_data({KEY_COMBAT_DRAFT: {}})

    # --- Финты (Feints) ---

    async def toggle_feint(self, feint_id: str) -> dict[str, Any]:
        """
        Переключает выбор финта (Radio Button).
        Если кликнули по уже выбранному -> снимаем выбор.
        """
        draft = await self.get_payload()

        current_feint = draft.get("feint_id")

        if current_feint == feint_id:
            draft.pop("feint_id", None)
        else:
            draft["feint_id"] = feint_id

        await self._save(draft)
        return draft

    # --- Способности (Abilities) ---

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
        Запоминает текущую цель атаки (если пользователь выбрал её вручную).
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
        Собирает данные драфта.
        Возвращает словарь с feint_id (если есть).
        Target ID и Action добавляются Оркестратором.
        """
        draft = await self.get_payload()

        payload = {}
        if "feint_id" in draft:
            payload["feint_id"] = draft["feint_id"]

        if "ability_id" in draft:
            payload["ability_id"] = draft["ability_id"]

        # Если цель была выбрана вручную, возвращаем её тоже
        if "target_id" in draft:
            payload["target_id"] = draft["target_id"]

        return payload

    # --- Helpers ---

    async def _save(self, draft_data: dict[str, Any]) -> None:
        await self.state.update_data({KEY_COMBAT_DRAFT: draft_data})
