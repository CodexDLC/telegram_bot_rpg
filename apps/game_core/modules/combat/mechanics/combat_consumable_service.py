# app/services/modules/combat/combat_consumable_service.py
from loguru import logger as log

from apps.common.schemas_dto import CombatActionResultDTO, CombatSessionContainerDTO
from apps.common.services.core_service import CombatManager


class ConsumableService:
    """
    Сервис для обработки логики использования расходуемых предметов (Consumables) в бою.
    Работает как статический класс, принимая на вход DTO актора и изменяя его.
    """

    @staticmethod
    def use_item(actor: CombatSessionContainerDTO, item_id: int) -> tuple[bool, str]:
        """
        Основной метод для использования предмета.
        """
        if not actor.state:
            return False, "Ошибка состояния бойца."

        # 1. Проверка блокировки на раунд
        if actor.state.consumable_used_this_round:
            log.warning(
                f"Consumable | char_id={actor.char_id} item_id={item_id} reason='Already used consumable this round'"
            )
            return False, "Вы уже использовали предмет в этом раунде."

        # 2. Найти предмет в быстрых слотах (поясе)
        item_to_use = next((item for item in actor.belt_items if item.inventory_id == item_id), None)
        if not item_to_use:
            log.warning(f"Consumable | char_id={actor.char_id} item_id={item_id} reason='Item not found in belt'")
            return False, "Предмет не найден на поясе."

        # 3. Проверка кулдауна
        if item_id in actor.state.item_cooldowns and actor.state.exchange_count < actor.state.item_cooldowns[item_id]:
            rounds_left = actor.state.item_cooldowns[item_id] - actor.state.exchange_count
            log.warning(
                f"Consumable | char_id={actor.char_id} item_id={item_id} reason='Item on cooldown' left={rounds_left}"
            )
            return False, f"Предмет на перезарядке. Осталось: {rounds_left} раунд(а)."

        # --- Все проверки пройдены, применяем эффекты ---
        log.info(f"Consumable | char_id={actor.char_id} item_id={item_id} item_name='{item_to_use.data.name}'")

        # 4. Применение эффектов (здесь можно будет вызывать под-методы)
        ConsumableService._apply_effects(actor, item_to_use)

        # 5. Установка флага блокировки на раунд
        actor.state.consumable_used_this_round = True

        # 6. Установка кулдауна (если есть)
        cooldown = getattr(item_to_use.data, "cooldown_rounds", 0)
        if cooldown > 0:
            actor.state.item_cooldowns[item_id] = actor.state.exchange_count + cooldown
            log.debug(
                f"Consumable | Cooldown set for item_id={item_id} until round={actor.state.item_cooldowns[item_id]}"
            )

        # 7. Уменьшение количества предмета
        item_to_use.quantity -= 1
        if item_to_use.quantity <= 0:
            log.info(f"Consumable | Item '{item_to_use.data.name}' ran out of stock.")

        return True, f"Вы использовали: {item_to_use.data.name}."

    @staticmethod
    def _apply_effects(actor: CombatSessionContainerDTO, item) -> None:
        """
        Применяет конкретные эффекты от предмета к состоянию актора.
        """
        if not actor.state:
            return

        # Восстановление HP
        restore_hp = getattr(item.data, "restore_hp", 0)
        if restore_hp > 0:
            max_hp = 1000  # Временная заглушка
            actor.state.hp_current = min(max_hp, actor.state.hp_current + restore_hp)
            log.debug(f"Consumable | Restored {restore_hp} HP for char_id={actor.char_id}")

        # Восстановление Энергии
        restore_energy = getattr(item.data, "restore_energy", 0)
        if restore_energy > 0:
            max_energy = 1000  # Временная заглушка
            actor.state.energy_current = min(max_energy, actor.state.energy_current + restore_energy)
            log.debug(f"Consumable | Restored {restore_energy} Energy for char_id={actor.char_id}")


class CombatConsumableService:
    """
    Обертка над ConsumableService для работы с Redis.
    Используется в CombatSessionService.
    """

    def __init__(self, combat_manager: CombatManager):
        self.combat_manager = combat_manager

    async def use_item(self, session_id: str, char_id: int, item_id: int) -> CombatActionResultDTO:
        # 1. Загружаем актора
        raw = await self.combat_manager.get_rbc_actor_state_json(session_id, char_id)
        if not raw:
            return CombatActionResultDTO(success=False, message="Actor not found")

        try:
            actor = CombatSessionContainerDTO.model_validate_json(raw)
        except Exception as e:  # noqa: BLE001
            log.error(f"Failed to parse actor: {e}")
            return CombatActionResultDTO(success=False, message="Data error")

        # 2. Применяем логику (Static)
        success, msg = ConsumableService.use_item(actor, item_id)

        # 3. Сохраняем, если успех
        if success:
            await self.combat_manager.set_rbc_actor_state_json(session_id, char_id, actor.model_dump_json())

        # updated_snapshot не возвращаем, так как SessionService сам его перечитает через ViewService
        return CombatActionResultDTO(success=success, message=msg, updated_snapshot=None)
