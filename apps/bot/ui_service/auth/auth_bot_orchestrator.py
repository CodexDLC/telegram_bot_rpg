from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.core_client.combat_rbc_client import CombatRBCClient
from apps.bot.core_client.exploration import ExplorationClient
from apps.bot.ui_service.combat.combat_bot_orchestrator import CombatBotOrchestrator
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import MessageCoordsDTO, ViewResultDTO
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.mesage_menu.menu_service import MenuService
from apps.bot.ui_service.tutorial.tutorial_service import TutorialServiceStats
from apps.bot.ui_service.tutorial.tutorial_service_skill import TutorialServiceSkills
from apps.common.schemas_dto.auth_dto import GameStage
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.arena_manager import ArenaManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.common.services.core_service.manager.world_manager import WorldManager
from apps.game_core.game_service.game_sync_service import GameSyncService
from apps.game_core.game_service.login_service import LoginService


class AuthViewDTO:
    """DTO для ответа оркестратора авторизации."""

    content: ViewResultDTO | None = None
    menu: ViewResultDTO | None = None
    new_state: str | None = None
    fsm_update: dict | None = None
    game_stage: str | None = None


class AuthBotOrchestrator:
    def __init__(
        self,
        session: AsyncSession,
        account_manager: AccountManager,
        combat_manager: CombatManager,
        arena_manager: ArenaManager,
        world_manager: WorldManager,
        exploration_client: ExplorationClient,
        combat_client: CombatRBCClient,
    ):
        self.session = session
        self.account_manager = account_manager
        self.combat_manager = combat_manager
        self.arena_manager = arena_manager
        self.world_manager = world_manager
        self.exploration_client = exploration_client
        self.combat_client = combat_client

    def get_content_coords(self, state_data: dict) -> MessageCoordsDTO | None:
        session_context = state_data.get(FSM_CONTEXT_KEY, {})
        content = session_context.get("message_content", {})
        if content:
            return MessageCoordsDTO(chat_id=content["chat_id"], message_id=content["message_id"])
        return None

    def get_menu_coords(self, state_data: dict) -> MessageCoordsDTO | None:
        session_context = state_data.get(FSM_CONTEXT_KEY, {})
        menu = session_context.get("message_menu", {})
        if menu:
            return MessageCoordsDTO(chat_id=menu["chat_id"], message_id=menu["message_id"])
        return None

    async def handle_login(self, char_id: int, state_data: dict) -> AuthViewDTO:
        """Обрабатывает вход персонажа в игру."""
        login_service = LoginService(char_id=char_id, state_data=state_data, account_manager=self.account_manager)
        login_result = await login_service.handle_login(session=self.session)

        result = AuthViewDTO()

        # Определяем стадию игры
        if isinstance(login_result, str):
            game_stage = login_result
        elif isinstance(login_result, tuple):
            game_stage = login_result[0]
        else:
            raise ValueError("Unknown login result format")

        result.game_stage = game_stage

        # Общая логика для меню (кроме создания персонажа)
        if game_stage != GameStage.CREATION:
            menu_service = MenuService(
                game_stage=game_stage if game_stage != "combat" else "in_game",  # Для боя меню специфичное, но пока так
                state_data=state_data,
                session=self.session,
                account_manager=self.account_manager,
            )
            text, kb = await menu_service.get_data_menu()
            result.menu = ViewResultDTO(text=text, kb=kb)

        # Логика по стадиям
        if game_stage == GameStage.TUTORIAL_STATS:
            tut_stats_service = TutorialServiceStats(char_id=char_id)
            text, kb = tut_stats_service.get_restart_stats()

            if text and kb:
                result.content = ViewResultDTO(text=text, kb=kb)
                result.new_state = "StartTutorial:start"
                result.fsm_update = {"bonus_dict": {}, "event_pool": None, "sim_text_count": 0}
            else:
                # Fallback, если что-то пошло не так
                result.content = ViewResultDTO(text="Ошибка загрузки туториала.", kb=None)

        elif game_stage == GameStage.TUTORIAL_SKILL:
            skill_choices_list: list[str] = []
            tut_skill_service = TutorialServiceSkills(skills_db=skill_choices_list)
            skill_text, skill_kb = tut_skill_service.get_start_data()
            if skill_text and skill_kb:
                result.content = ViewResultDTO(text=skill_text, kb=skill_kb)
                result.new_state = "StartTutorial:in_skills_progres"
                result.fsm_update = {"skill_choices_list": skill_choices_list}

        elif game_stage == "combat":
            # Восстановление боя
            # Нам нужно получить session_id из аккаунта
            ac_data = await self.account_manager.get_account_data(char_id)
            combat_session_id = ac_data.get("combat_session_id") if ac_data else None

            if combat_session_id:
                combat_orchestrator = CombatBotOrchestrator(
                    client=self.combat_client,
                    account_manager=self.account_manager,
                    exploration_client=self.exploration_client,
                    arena_manager=self.arena_manager,
                    combat_manager=self.combat_manager,
                    world_manager=self.world_manager,
                )

                # Получаем вид боя
                combat_view = await combat_orchestrator.get_dashboard_view(combat_session_id, char_id, {}, state_data)

                result.content = combat_view.content
                result.menu = combat_view.menu  # Переопределяем меню, так как в бою оно свое (лог)
                result.new_state = "InGame:combat"
                result.fsm_update = {"combat_session_id": combat_session_id}

                if combat_view.target_id:
                    result.fsm_update["combat_target_id"] = combat_view.target_id

        elif game_stage == "in_game" or (isinstance(login_result, tuple) and login_result[0] == "in_game"):
            # Вход в игру (Навигация)
            sync_service = GameSyncService(self.session, self.account_manager)
            await sync_service.synchronize_player_state(char_id)

            # session_context = state_data.get(FSM_CONTEXT_KEY, {}) # Удалено: не используется
            # actor_name = session_context.get("symbiote_name", "Симбиот") # Удалено: не используется

            # Нам нужно получить текущую локацию.
            from apps.bot.ui_service.exploration.exploration_bot_orchestrator import ExplorationBotOrchestrator

            expl_orchestrator = ExplorationBotOrchestrator(self.exploration_client, self.combat_client)

            expl_view = await expl_orchestrator.get_current_view(char_id, state_data)

            result.content = expl_view.content
            result.new_state = "InGame:navigation"

        return result
