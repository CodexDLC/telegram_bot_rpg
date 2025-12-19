import time
from contextlib import suppress
from typing import cast

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InaccessibleMessage, InlineKeyboardMarkup
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.core_client.combat_rbc_client import CombatRBCClient
from apps.bot.core_client.exploration import ExplorationClient
from apps.bot.resources.fsm_states import ArenaState, InGame
from apps.bot.resources.keyboards.combat_callback import CombatActionCallback
from apps.bot.ui_service.combat.combat_bot_orchestrator import CombatBotOrchestrator
from apps.bot.ui_service.combat.combat_ui_service import CombatUIService
from apps.bot.ui_service.exploration.exploration_ui import ExplorationUIService
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from apps.bot.ui_service.hub_entry_service import HubEntryService
from apps.bot.ui_service.menu_service import MenuService
from apps.common.schemas_dto import SessionDataDTO
from apps.common.schemas_dto.combat_source_dto import CombatMoveDTO
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.arena_manager import ArenaManager
from apps.common.services.core_service.manager.combat_manager import CombatManager

action_router = Router(name="combat_actions")


@action_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "submit"))
async def submit_turn_handler(call: CallbackQuery, state: FSMContext, combat_rbc_client: CombatRBCClient, bot: Bot):
    """
    Хэндлер подтверждения хода (Submit).
    Отправляет ход, запускает анимацию ожидания и обновляет UI по завершении.
    """
    if not call.message or isinstance(call.message, InaccessibleMessage):
        return await call.answer("Сообщение недоступно.")

    await call.answer("Ход отправлен!")
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content = session_context.get("message_content")
    message_menu = session_context.get("message_menu")

    # Читаем из session_context
    char_id = session_context.get("char_id")
    session_id = session_context.get("combat_session_id")

    target_id = state_data.get("combat_target_id")
    selection = state_data.get("combat_selection", {})

    if not char_id or not session_id or not target_id:
        return await Err.report_and_restart(call, "Данные сессии боя утеряны.")

    # Создаем оркестратор вручную
    ui = CombatUIService(state_data, char_id)
    orchestrator = CombatBotOrchestrator(combat_rbc_client, ui)

    # --- Зоны защиты ---
    def_zones_raw = selection.get("def", [])
    real_def_zones = def_zones_raw[0].split("_") if def_zones_raw else []

    move_dto = CombatMoveDTO(
        target_id=int(target_id),
        attack_zones=selection.get("atk", []),
        block_zones=real_def_zones,
        ability_key=state_data.get("combat_selected_ability"),
        execute_at=int(time.time()) + 60,
    )

    try:
        # 1. Отправляем ход в ядро
        # handle_submit регистрирует ход и возвращает текущее состояние (обычно waiting)
        _, _, (log_text, log_kb) = await orchestrator.handle_submit(session_id, char_id, move_dto)

        # Сбрасываем выбор в FSM
        await state.update_data(combat_selection={}, combat_selected_ability=None)

        # 2. Обновляем лог боя (нижнее сообщение) сразу, чтобы показать, что ход принят
        with suppress(TelegramAPIError):
            if message_menu:
                await bot.edit_message_text(
                    chat_id=message_menu["chat_id"],
                    message_id=message_menu["message_id"],
                    text=log_text,
                    reply_markup=log_kb,
                    parse_mode="HTML",
                )

        # 3. Запускаем анимацию ожидания на основном экране (верхнее сообщение)
        session_dto = SessionDataDTO(
            user_id=call.from_user.id, char_id=char_id, message_content=message_content, message_menu=message_menu
        )
        anim_service = UIAnimationService(bot, session_dto)

        async def check_combat(step: int):
            # Просто проверяем статус: если не waiting - значит что-то произошло
            return await orchestrator.check_combat_status(session_id, char_id)

        # Поллинг с анимацией (30 секунд: 15 шагов по 2 сек)
        # result может быть None или тем, что возвращает check_combat (FullViewResult)
        result = await anim_service.animate_polling(
            base_text="⚔️ <b>Бой в разгаре!</b>\nОжидание хода противника...",
            check_func=check_combat,
            steps=15,
            step_delay=2.0,
        )

        # 4. Обработка результата
        if result:
            # Бой обновился (пришел ответный удар или конец боя)
            # result is FullViewResult: tuple[int | None, tuple[str, InlineKeyboardMarkup], tuple[str, InlineKeyboardMarkup]]
            # Мы должны явно указать mypy, что это кортеж из 3 элементов
            # Но так как animate_polling возвращает Any (или то что вернет check_func), mypy может путаться.
            # check_combat возвращает FullViewResult | None.
            # Значит result здесь FullViewResult.

            # Распаковка
            # Мы знаем, что result это кортеж из 3 элементов, но mypy видит Any
            # Поэтому мы можем явно скастить или просто распаковать, если mypy не ругается на Any
            # Но mypy ругался на "Unpacking a string is disallowed", значит он думал, что result это строка?
            # animate_polling возвращает Any | None.

            # Явно приведем тип, чтобы mypy успокоился
            # FullViewResult = tuple[int | None, tuple[str, InlineKeyboardMarkup], tuple[str, InlineKeyboardMarkup]]

            # Но мы не можем импортировать FullViewResult из orchestrator, так как это создаст циклический импорт
            # (orchestrator импортирует ui_service, который импортирует orchestrator...)
            # Поэтому просто используем индексы или cast

            res_tuple = cast(tuple, result)
            new_target_id = res_tuple[0]
            content_view = res_tuple[1]
            menu_view = res_tuple[2]

            content_text = cast(str, content_view[0])
            content_kb = cast(InlineKeyboardMarkup, content_view[1])
            menu_text = cast(str, menu_view[0])
            menu_kb = cast(InlineKeyboardMarkup, menu_view[1])

            if new_target_id is not None:
                await state.update_data(combat_target_id=new_target_id)

            # Обновляем основное сообщение
            with suppress(TelegramAPIError):
                if message_content:
                    await bot.edit_message_text(
                        chat_id=message_content["chat_id"],
                        message_id=message_content["message_id"],
                        text=content_text,
                        reply_markup=content_kb,
                        parse_mode="HTML",
                    )

            # Обновляем лог (там может быть инфо об уроне)
            with suppress(TelegramAPIError):
                if message_menu:
                    await bot.edit_message_text(
                        chat_id=message_menu["chat_id"],
                        message_id=message_menu["message_id"],
                        text=menu_text,
                        reply_markup=menu_kb,
                        parse_mode="HTML",
                    )
        else:
            # Таймаут: восстанавливаем интерфейс (кнопку Refresh)
            # Запрашиваем актуальный вид (скорее всего всё еще waiting)
            _, (content_text, content_kb), _ = await orchestrator.get_dashboard_view(session_id, char_id, {})
            with suppress(TelegramAPIError):
                if message_content:
                    await bot.edit_message_text(
                        chat_id=message_content["chat_id"],
                        message_id=message_content["message_id"],
                        text=content_text,
                        reply_markup=content_kb,
                        parse_mode="HTML",
                    )

    except Exception as e:  # noqa: BLE001
        log.exception(f"ActionHandler | status=failed char_id={char_id} error={e}")
        await Err.report_and_restart(call, "Не удалось отправить ход в Ядро.")


@action_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "refresh"))
async def refresh_combat_handler(call: CallbackQuery, state: FSMContext, combat_rbc_client: CombatRBCClient, bot: Bot):
    """
    Хэндлер ручного обновления экрана боя. Обновляет ОБА сообщения.
    """
    if not call.message or isinstance(call.message, InaccessibleMessage):
        return await call.answer("Сообщение недоступно.")

    await call.answer("Обновляю...")
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content = session_context.get("message_content")
    message_menu = session_context.get("message_menu")

    # Читаем из session_context
    char_id = session_context.get("char_id")
    session_id = session_context.get("combat_session_id")

    selection = state_data.get("combat_selection", {})

    if not char_id or not session_id:
        return await Err.report_and_restart(call, "Данные сессии боя утеряны.")

    # Создаем оркестратор вручную
    ui = CombatUIService(state_data, char_id)
    orchestrator = CombatBotOrchestrator(combat_rbc_client, ui)

    try:
        # 1. Оркестратор возвращает данные для двух сообщений
        new_target_id, (content_text, content_kb), (menu_text, menu_kb) = await orchestrator.get_dashboard_view(
            session_id, char_id, selection
        )

        # Обновляем target_id в FSM, если он изменился
        if new_target_id is not None:
            await state.update_data(combat_target_id=new_target_id)

        # 2. Обновляем контентное сообщение
        with suppress(TelegramAPIError):
            if message_content:
                await bot.edit_message_text(
                    chat_id=message_content["chat_id"],
                    message_id=message_content["message_id"],
                    text=content_text,
                    reply_markup=content_kb,
                    parse_mode="HTML",
                )

        # 3. Обновляем сообщение с логом боя
        with suppress(TelegramAPIError):
            if message_menu:
                await bot.edit_message_text(
                    chat_id=message_menu["chat_id"],
                    message_id=message_menu["message_id"],
                    text=menu_text,
                    reply_markup=menu_kb,
                    parse_mode="HTML",
                )

    except Exception as e:  # noqa: BLE001
        log.error(f"ActionHandler | refresh failed: {e}")
        await Err.report_and_restart(call, "Сбой при получении данных боя.")


@action_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "leave"))
async def leave_combat_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    exploration_client: ExplorationClient,
    session: AsyncSession,
    account_manager: AccountManager,
    arena_manager: ArenaManager,
    combat_manager: CombatManager,
):
    """
    Завершает участие в бою и переводит игрока в предыдущее состояние (Навигация или Арена).
    """
    if not call.message or isinstance(call.message, InaccessibleMessage):
        return await call.answer("Сообщение недоступно.")

    await call.answer("Возвращение...")

    # 1. Получаем контекст сессии
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})

    # Читаем сохраненное предыдущее состояние
    prev_state_str = session_context.get("previous_state", "InGame:navigation")

    # Определяем, куда возвращаться
    if prev_state_str == "ArenaState:menu":
        target_state = ArenaState.menu
        is_arena = True
    else:
        target_state = InGame.navigation
        is_arena = False

    await state.set_state(target_state)

    # 2. Очистка данных боя
    char_id = session_context.get("char_id")
    message_content = session_context.get("message_content")
    message_menu = session_context.get("message_menu")
    actor_name = session_context.get("symbiote_name", "Симбиот")

    # Очищаем ID сессии боя
    session_context["combat_session_id"] = None
    # Очищаем previous_state, чтобы не засорять
    session_context["previous_state"] = None

    await state.update_data({FSM_CONTEXT_KEY: session_context})
    await state.update_data(combat_session_id=None, combat_target_id=None, combat_selection={})

    if not char_id or not message_content:
        return await Err.report_and_restart(call, "Ошибка контекста при выходе из боя.")

    # 3. Отрисовка интерфейса в зависимости от того, куда вернулись
    try:
        if is_arena:
            # Если вернулись на Арену - используем HubEntryService для отрисовки меню арены
            hub_service = HubEntryService(
                char_id=char_id,
                target_loc="svc_arena_main",  # <--- ИСПРАВЛЕНО: Правильный ключ из HUB_CONFIGS
                state_data=state_data,
                session=session,
                account_manager=account_manager,
                arena_manager=arena_manager,
                combat_manager=combat_manager,
            )
            # Рендерим меню арены
            arena_text, arena_kb, _ = await hub_service.render_hub_menu()

            await bot.edit_message_text(
                chat_id=message_content["chat_id"],
                message_id=message_content["message_id"],
                text=arena_text,
                reply_markup=arena_kb,
                parse_mode="HTML",
            )
        else:
            # Если вернулись в мир - рисуем навигацию
            expl_ui = ExplorationUIService(exploration_client)
            nav_text, nav_kb = await expl_ui.render_map(char_id, actor_name)

            if nav_text:
                await bot.edit_message_text(
                    chat_id=message_content["chat_id"],
                    message_id=message_content["message_id"],
                    text=nav_text,
                    reply_markup=nav_kb,
                    parse_mode="HTML",
                )
    except Exception as e:  # noqa: BLE001
        log.error(f"LeaveCombat | Failed to render target UI: {e}")
        await bot.edit_message_text(
            chat_id=message_content["chat_id"],
            message_id=message_content["message_id"],
            text="🗺 <b>Вы вернулись.</b>\nИспользуйте меню.",
            reply_markup=None,
            parse_mode="HTML",
        )

    # 4. Очистка нижнего сообщения (меню/лог) -> Возврат к Главному Меню
    try:
        if message_menu:
            # Используем MenuService для отрисовки главного меню (инвентарь, перс и т.д.)
            menu_service = MenuService(
                game_stage="in_game", state_data=state_data, session=session, account_manager=account_manager
            )
            menu_text, menu_kb = await menu_service.get_data_menu()

            await bot.edit_message_text(
                chat_id=message_menu["chat_id"],
                message_id=message_menu["message_id"],
                text=menu_text,
                reply_markup=menu_kb,
                parse_mode="HTML",
            )
    except Exception as e:  # noqa: BLE001
        log.warning(f"LeaveCombat | Failed to restore main menu: {e}")
