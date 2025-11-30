# app/services/game_service/hub_entry_service.py

from aiogram.fsm.state import State
from aiogram.utils.keyboard import InlineKeyboardMarkup
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import InGame  # Для использования FSM.state в случае ошибки
from app.resources.game_data.hub_config import HUB_CONFIGS
from app.services.ui_service.base_service import BaseUIService  # Для наследования общих методов (например, логирование)


class HubEntryService(BaseUIService):  # Наследуем от BaseUIService для стандартизации
    """
    Сервис-диспетчер, который активирует вход в Сервисные Хабы (Арена, Банк и т.д.)
    на основе ключа target_loc из конфигурации.
    """

    def __init__(self, char_id: int, target_loc: str, state_data: dict, session: AsyncSession):
        # BaseUIService.__init__ поможет в будущем
        super().__init__(char_id=char_id, state_data=state_data)
        self.target_loc = target_loc
        self.session = session
        log.debug(f"Инициализирован HubEntryService для char_id={char_id}, хаб: {target_loc}.")

    async def render_hub_menu(self) -> tuple[str, InlineKeyboardMarkup | None, State]:
        """
        Главный метод. Извлекает конфигурацию из HUB_CONFIGS, динамически
        создает и вызывает UI-билдер, возвращая готовый контент и новое FSM-состояние.

        Returns:
            tuple[str, InlineKeyboardMarkup | None, State]: (text, keyboard, new_fsm_state)
        """

        # --- 1. Поиск конфигурации и валидация ---
        config = HUB_CONFIGS.get(self.target_loc)
        default_fsm_state = InGame.navigation

        if not config:
            log.warning(f"Конфигурация для хаба '{self.target_loc}' не найдена в HUB_CONFIGS.")
            # Возврат в безопасное состояние
            return "Неизвестная ошибка. Целевой хаб не найден.", None, default_fsm_state

        log.debug(f"Конфигурация для хаба '{self.target_loc}' успешно загружена.")

        new_fsm_state = config.get("fsm_state", default_fsm_state)

        try:
            # 2. Динамическое извлечение класса
            method_name = config.get("render_method_name", "render_menu")
            builder_class = config.get("ui_builder_class")

            if not builder_class:
                log.error(f"В конфигурации хаба '{self.target_loc}' отсутствует ui_builder_class.")
                return "Ошибка конфигурации: отсутствует билдер UI.", None, new_fsm_state

            # 2. Создаем экземпляр билдера
            ui_builder = builder_class(self.char_id, self.session, self.state_data)

            # 3. Динамически получаем ссылку на метод
            render_method = getattr(ui_builder, method_name, None)

            if render_method is None:
                log.error(f"Метод '{method_name}' не найден в классе {builder_class.__name__}.")
                # Возвращаем ошибку, так как контракт нарушен
                return "Ошибка: нарушен контракт метода.", None, new_fsm_state

            # 4. Вызываем найденный метод
            text, kb = await render_method()

            return text, kb, new_fsm_state

        except (AttributeError, TypeError) as e:
            log.exception(f"Критическая ошибка при динамическом вызове билдера UI для хаба '{self.target_loc}': {e}")
            # Возврат в безопасное состояние при критической ошибке
            return (
                "Критический сбой при запуске сервиса. Попробуйте выйти и войти снова.",
                None,
                new_fsm_state,
            )
