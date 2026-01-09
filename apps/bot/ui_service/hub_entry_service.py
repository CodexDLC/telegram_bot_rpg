from aiogram.fsm.state import State
from aiogram.utils.keyboard import InlineKeyboardMarkup
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import BotState
from apps.bot.resources.hub_config import HUB_CONFIGS
from apps.bot.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from apps.bot.ui_service.base_service import BaseUIService
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.services.redis.manager.account_manager import AccountManager
from apps.common.services.redis.manager.arena_manager import ArenaManager
from apps.common.services.redis.manager.combat_manager import CombatManager


class HubEntryService(BaseUIService):
    """
    Сервис-диспетчер для активации входа в различные сервисные хабы (Арена, Банк и т.д.).

    Использует конфигурацию из `HUB_CONFIGS` для динамического вызова
    соответствующих UI-билдеров и управления FSM-состояниями.
    """

    def __init__(
        self,
        char_id: int,
        target_loc: str,
        state_data: dict,
        session: AsyncSession,
        account_manager: AccountManager,
        arena_manager: ArenaManager,
        combat_manager: CombatManager,
    ):
        super().__init__(char_id=char_id, state_data=state_data)
        self.target_loc = target_loc
        self.session = session
        self.account_manager = account_manager
        self.arena_manager = arena_manager
        self.combat_manager = combat_manager
        log.debug(f"HubEntryService | status=initialized char_id={char_id} target_loc='{self.target_loc}'")

    async def render_hub_menu(self) -> tuple[str, InlineKeyboardMarkup | None, State]:
        """
        Извлекает конфигурацию хаба, динамически создает и вызывает UI-билдер,
        возвращая готовый контент и новое FSM-состояние.
        """
        config = HUB_CONFIGS.get(self.target_loc)
        default_fsm_state = BotState.exploration  # ИСПРАВЛЕНО: InGame.exploration

        if not config:
            log.warning(f"HubEntryService | status=failed reason='Config not found' target_loc='{self.target_loc}'")
            return "Неизвестная ошибка. Целевой хаб не найден.", None, default_fsm_state

        log.debug(f"HubEntryService | event=config_loaded target_loc='{self.target_loc}'")
        new_fsm_state = config.get("fsm_state", default_fsm_state)

        try:
            builder_class = config.get("ui_builder_class")
            if not builder_class:
                log.error(
                    f"HubEntryService | status=failed reason='ui_builder_class missing in config' target_loc='{self.target_loc}'"
                )
                return "Ошибка конфигурации: отсутствует билдер UI.", None, new_fsm_state

            # --- НОВАЯ ЛОГИКА: Динамическое создание зависимостей ---

            # 1. Определяем все возможные зависимости, которые может предоставить этот сервис
            all_dependencies = {
                "char_id": self.char_id,
                "session": self.session,
                "state_data": self.state_data,
                "account_manager": self.account_manager,
                "arena_manager": self.arena_manager,
                "combat_manager": self.combat_manager,
                # Используем дефолтное имя, так как в BaseUIService его больше нет
                "actor_name": self.state_data.get(FSM_CONTEXT_KEY, {}).get("symbiote_name", DEFAULT_ACTOR_NAME),
                "title": config.get("title", "Хаб"),  # <-- Добавляем title из конфига
            }

            # 2. Получаем список требуемых зависимостей из конфига
            required_deps_names = config.get("required_dependencies", [])

            # 3. Собираем словарь аргументов только для нужных зависимостей
            builder_kwargs = {
                dep_name: all_dependencies[dep_name] for dep_name in required_deps_names if dep_name in all_dependencies
            }

            # 4. Создаем экземпляр с нужными аргументами
            ui_builder = builder_class(**builder_kwargs)

            # --- КОНЕЦ НОВОЙ ЛОГИКИ ---

            method_name = config.get("render_method_name", "render_menu")
            render_method = getattr(ui_builder, method_name, None)

            if render_method is None:
                log.error(
                    f"HubEntryService | status=failed reason='Render method not found' method='{method_name}' class='{builder_class.__name__}'"
                )
                return "Ошибка: нарушен контракт метода.", None, new_fsm_state

            # ИСПРАВЛЕНИЕ: Обработка ViewResultDTO
            result = await render_method()

            if isinstance(result, ViewResultDTO):
                return result.text, result.kb, new_fsm_state
            elif isinstance(result, tuple) and len(result) == 2:
                return result[0], result[1], new_fsm_state
            else:
                log.error(f"HubEntryService | status=failed reason='Unexpected return type' type='{type(result)}'")
                return "Ошибка: некорректный ответ от UI-сервиса.", None, new_fsm_state

        except (AttributeError, TypeError, KeyError) as e:
            log.exception(
                f"HubEntryService | status=failed reason='Dynamic UI builder call error' target_loc='{self.target_loc}' error='{e}'"
            )
            return (
                "Критический сбой при запуске сервиса. Попробуйте выйти и войти снова.",
                None,
                new_fsm_state,
            )
