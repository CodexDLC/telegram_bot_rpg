# app/services/game_service/combat/consumable_service.py
from loguru import logger as log

from app.resources.schemas_dto.combat_source_dto import CombatSessionContainerDTO


class ConsumableService:
    """
    Сервис для обработки логики использования расходуемых предметов (Consumables) в бою.
    Работает как статический класс, принимая на вход DTO актора и изменяя его.
    """

    @staticmethod
    def use_item(actor: CombatSessionContainerDTO, item_id: int) -> tuple[bool, str]:
        """
        Основной метод для использования предмета.

        Проверяет все условия (блокировки, кулдауны), применяет эффекты
        и обновляет состояние актора.

        Args:
            actor: DTO участника боя, который использует предмет.
            item_id: Уникальный ID предмета в инвентаре.

        Returns:
            Кортеж (успех, сообщение для пользователя).
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
        # (Пока не удаляем, если кончился, это может сделать другой сервис после боя)
        item_to_use.quantity -= 1
        if item_to_use.quantity <= 0:
            # Можно добавить флаг "to_delete", чтобы потом удалить
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
            # TODO: [Temporary] Заменить заглушку на динамический расчет max_hp из статов
            # max_hp = int(StatsCalculator.calculate("hp_max", actor.stats.get("hp_max", StatSourceData(base=1))))
            max_hp = 1000  # Временная заглушка
            actor.state.hp_current = min(max_hp, actor.state.hp_current + restore_hp)
            log.debug(f"Consumable | Restored {restore_hp} HP for char_id={actor.char_id}")

        # Восстановление Энергии
        restore_energy = getattr(item.data, "restore_energy", 0)
        if restore_energy > 0:
            # TODO: [Temporary] Заменить заглушку на динамический расчет max_energy из статов
            # max_energy = int(StatsCalculator.calculate("energy_max", actor.stats.get("energy_max", StatSourceData(base=1))))
            max_energy = 1000  # Временная заглушка
            actor.state.energy_current = min(max_energy, actor.state.energy_current + restore_energy)
            log.debug(f"Consumable | Restored {restore_energy} Energy for char_id={actor.char_id}")

        # TODO: Добавить логику для наложения баффов/дебаффов (item.data.effects)
        # Это потребует добавления эффектов в actor.state.effects
        # Например: actor.state.effects["strength_buff"] = {"duration": 3, "value": 10}
