from aiogram.fsm.state import State
from aiogram.utils.keyboard import InlineKeyboardMarkup
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import InGame
from app.resources.game_data.hub_config import HUB_CONFIGS
from app.services.ui_service.base_service import BaseUIService


class HubEntryService(BaseUIService):
    """
    Сервис-диспетчер для активации входа в различные сервисные хабы (Арена, Банк и т.д.).

    Использует конфигурацию из `HUB_CONFIGS` для динамического вызова
    соответствующих UI-билдеров и управления FSM-состояниями.
    """

    def __init__(self, char_id: int, target_loc: str, state_data: dict, session: AsyncSession):
        """
        Инициализирует HubEntryService.

        Args:
            char_id: Уникальный идентификатор персонажа.
            target_loc: Идентификатор целевой локации/хаба.
            state_data: Текущие данные FSM-состояния.
            session: Асинхронная сессия базы данных.
        """
        super().__init__(char_id=char_id, state_data=state_data)
        self.target_loc = target_loc
        self.session = session
        log.debug(f"HubEntryService | status=initialized char_id={char_id} target_loc='{target_loc}'")

    async def render_hub_menu(self) -> tuple[str, InlineKeyboardMarkup | None, State]:
        """
        Извлекает конфигурацию хаба, динамически создает и вызывает UI-билдер,
        возвращая готовый контент и новое FSM-состояние.

        Returns:
            Кортеж, содержащий:
            - text: Текст для отображения в меню хаба.
            - keyboard: Клавиатура для меню хаба, или None.
            - new_fsm_state: Новое FSM-состояние, в которое должен перейти бот.

        Raises:
            AttributeError: Если указанный метод рендеринга не найден в UI-билдере.
            TypeError: Если UI-билдер или его метод вызываются с некорректными аргументами.
        """
        config = HUB_CONFIGS.get(self.target_loc)
        default_fsm_state = InGame.navigation

        if not config:
            log.warning(f"HubEntryService | status=failed reason='Config not found' target_loc='{self.target_loc}'")
            return "Неизвестная ошибка. Целевой хаб не найден.", None, default_fsm_state

        log.debug(f"HubEntryService | event=config_loaded target_loc='{self.target_loc}'")
        new_fsm_state = config.get("fsm_state", default_fsm_state)

        try:
            method_name = config.get("render_method_name", "render_menu")
            builder_class = config.get("ui_builder_class")

            if not builder_class:
                log.error(
                    f"HubEntryService | status=failed reason='ui_builder_class missing in config' target_loc='{self.target_loc}'"
                )
                return "Ошибка конфигурации: отсутствует билдер UI.", None, new_fsm_state

            ui_builder = builder_class(char_id=self.char_id, session=self.session, state_data=self.state_data)
            render_method = getattr(ui_builder, method_name, None)

            if render_method is None:
                log.error(
                    f"HubEntryService | status=failed reason='Render method not found' method='{method_name}' class='{builder_class.__name__}'"
                )
                return "Ошибка: нарушен контракт метода.", None, new_fsm_state

            text, kb = await render_method()
            return text, kb, new_fsm_state

        except (AttributeError, TypeError) as e:
            log.exception(
                f"HubEntryService | status=failed reason='Dynamic UI builder call error' target_loc='{self.target_loc}' error='{e}'"
            )
            return (
                "Критический сбой при запуске сервиса. Попробуйте выйти и войти снова.",
                None,
                new_fsm_state,
            )
