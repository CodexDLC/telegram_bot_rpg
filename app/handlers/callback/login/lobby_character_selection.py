# app/handlers/callback/login/lobby_character_selection.py
import asyncio
from typing import Any

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.callback.login.char_creation import start_creation_handler
from app.handlers.callback.ui.status_menu.character_status import show_status_tab_logic
from app.resources.fsm_states.states import CharacterLobby, InGame, StartTutorial
from app.resources.keyboards.callback_data import LobbySelectionCallback
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
from app.resources.texts.buttons_callback import GameStage
from app.services.game_service.login_service import LoginService
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import (
    FSM_CONTEXT_KEY,
    fsm_clean_core_state,
    fsm_load_auto,
    fsm_store,
)
from app.services.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from app.services.ui_service.lobby_service import LobbyService
from app.services.ui_service.menu_service import MenuService
from app.services.ui_service.navigation_service import NavigationService
from app.services.ui_service.tutorial.tutorial_service import TutorialServiceStats
from app.services.ui_service.tutorial.tutorial_service_skill import TutorialServiceSkills

router = Router(name="lobby_fsm")


@router.callback_query(CharacterLobby.selection, LobbySelectionCallback.filter(F.action.in_({"select", "delete"})))
async def select_or_delete_character_handler(
    call: CallbackQuery, callback_data: LobbySelectionCallback, state: FSMContext, bot: Bot, session: AsyncSession
) -> None:
    """
    Обрабатывает ВЫБОР или УДАЛЕНИЕ персонажа в лобби.

    При 'select': Загружает данные, обновляет список, показывает статус.
    При 'delete': Запрашивает подтверждение на удаление (пока заглушка).

    Args:
        call (CallbackQuery): Callback от выбора персонажа.
        callback_data (LobbySelectionCallback): Данные обратного вызова.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        session (AsyncSession): Сессия базы данных.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'select_or_delete_character_handler' получил обновление без 'from_user'.")
        return

    # --- 2. ОБЩИЙ БЛОК: Загрузка данных (нужен для обоих) ---
    char_id = callback_data.char_id
    user = call.from_user
    action = callback_data.action

    log.info(
        f"Хэндлер 'select_or_delete_character_handler' [lobby:{action}] вызван user_id={user.id}, char_id={char_id}"
    )

    # Отвечаем на call сразу (важно для delete, чтобы убрать часики)
    await call.answer()
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})

    current_char_id_in_fsm = session_context.get("char_id")
    if action == "select" and char_id == current_char_id_in_fsm:
        log.debug(f"User {user.id} повторно нажал на уже выбранного персонажа {char_id}. Игнорируем.")
        return

    # Инициализируем сервис
    lobby_service = LobbyService(user=user, char_id=char_id, state_data=state_data)

    # Пытаемся получить список персонажей из FSM.
    characters = await fsm_load_auto(state=state, key="characters")

    # Если в FSM данных нет, загружаем их из БД.
    if characters is None:
        log.info(f"Данные 'characters' для user_id={user.id} не найдены в FSM, загрузка из БД...")
        characters = await lobby_service.get_data_characters(session)
        # Сохраняем в FSM
        if characters:
            await state.update_data(characters=await fsm_store(value=characters))

    # --- 3. РАЗДЕЛЕНИЕ ЛОГИКИ (if/elif) ---

    if action == "select":
        if not char_id:
            await Err.generic_error(call=call)
            return
        # --- 4. ЛОГИКА "SELECT" (твой готовый код) ---
        if characters:
            text, kb = lobby_service.get_data_lobby_start(characters)

            message_menu: dict[str, Any] | None = session_context.get("message_menu")
            log.debug(f"message_menu = {message_menu} ")

            if message_menu:
                await bot.edit_message_text(
                    chat_id=message_menu.get("chat_id"),
                    message_id=message_menu.get("message_id"),
                    text=text,
                    parse_mode="html",
                    reply_markup=kb,
                )

            # (Исправленный вызов, как мы обсуждали)
            fsm_data = await lobby_service.get_fsm_data(characters)
            current_data = await state.get_data()
            session_context = current_data.get(FSM_CONTEXT_KEY, {})
            session_context["char_id"] = fsm_data.get("char_id")
            session_context["user_id"] = fsm_data.get("user_id")
            await state.update_data({FSM_CONTEXT_KEY: session_context})
            await state.update_data(characters=fsm_data.get("characters"))

            # Вызываем обработчик меню статуса для отображения информации.
            await show_status_tab_logic(char_id=char_id, state=state, bot=bot, call=call, key="bio", session=session)
        else:
            log.warning(f"У user_id={user.id} нет персонажей, хотя он находится в лобби выбора.")
            await Err.generic_error(call=call)

    elif action == "delete":
        # --- 5. ЛОГИКА "DELETE" (новая) ---
        log.debug(f"Запрос на удаление [lobby:delete] для char_id={char_id}.")

        # Проверяем, что персонаж вообще выбран
        if not char_id:
            log.warning(f"User {user.id} нажал 'delete', не выбрав персонажа.")
            await call.answer("Сначала выберите персонажа, которого хотите удалить", show_alert=True)
            return

            # 1. Получаем message_content (где висит статус)
        message_content = session_context.get("message_content")

        if not isinstance(message_content, dict):
            log.error(f"User {user.id}: Не найден 'message_content' для показа подтверждения удаления.")
            await Err.message_content_not_found_in_fsm(call)
            return

        char_name = "???"
        if characters:
            for char in characters:
                if char.character_id == char_id:
                    char_name = char.name
                    break

        await state.set_state(CharacterLobby.confirm_delete)

        text, kb = lobby_service.get_message_delete(char_name)

        await state.update_data(char_name=char_name)

        message_content = lobby_service.get_message_content_data()

        if message_content is None:
            log.error(f"User {user.id}: Не найден 'message_content' для показа подтверждения удаления.")
            await Err.message_content_not_found_in_fsm(call)
            return

        chat_id, message_id = message_content

        if chat_id and message_id:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, parse_mode="html", reply_markup=kb
            )


@router.callback_query(CharacterLobby.confirm_delete, LobbySelectionCallback.filter())
async def confirm_delete_handler(
    call: CallbackQuery, state: FSMContext, callback_data: LobbySelectionCallback, bot: Bot, session: AsyncSession
) -> None:
    """
    Обрабатывает подтверждение ("Да") или отмену ("Нет") удаления персонажа.

    Args:
        call (CallbackQuery): Входящий callback.
        state (FSMContext): Состояние FSM.
        callback_data (LobbySelectionCallback): Данные обратного вызова.
        bot (Bot): Экземпляр бота.
        session (AsyncSession): Сессия базы данных.
    """

    if not call.from_user or not call.message:
        log.warning("Хэндлер 'confirm_delete_handler' получил обновление без 'from_user' или 'message'.")
        return

    await call.answer()  # Отвечаем на call в любом случае

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    # char_id для "Нет" берем из callback, для "Да" - лучше из state
    char_id = callback_data.char_id or session_context.get("char_id")
    user = call.from_user

    if not char_id:
        log.error(f"User {user.id}: Не найден char_id в confirm_delete_handler.")
        await Err.generic_error(call)
        return

    lobby_service = LobbyService(user=user, char_id=char_id, state_data=state_data)

    if callback_data.action == "delete_yes":
        log.info(f"User {user.id} подтвердил удаление персонажа {char_id}.")

        # 1. Удаляем персонажа из БД
        delete_success = await lobby_service.delete_character(session)

        if not delete_success:
            log.error(f"Не удалось удалить персонажа {char_id} из БД.")
            await Err.generic_error(call)
            return

        # 2. Обновляем список персонажей в FSM
        characters = await lobby_service.get_data_characters(session)
        await state.update_data(characters=await fsm_store(value=characters))

        # 3. Обновляем UI
        # Верхнее сообщение (список персонажей)
        text_lobby, kb_lobby = lobby_service.get_data_lobby_start(characters)
        message_menu_data = lobby_service.get_message_menu_data()
        if message_menu_data:
            chat_id, message_id = message_menu_data
            if chat_id and message_id:
                await bot.edit_message_text(
                    chat_id=chat_id, message_id=message_id, text=text_lobby, reply_markup=kb_lobby
                )

        # Нижнее сообщение (статус)
        message_content_data = lobby_service.get_message_content_data()
        if message_content_data:
            chat_id, message_id = message_content_data
            if chat_id and message_id:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="Персонаж удален. Выберите другого персонажа или создайте нового.",
                    reply_markup=None,
                )

        # 4. Сбрасываем char_id в FSM
        session_context["char_id"] = None
        await state.update_data({FSM_CONTEXT_KEY: session_context})

        # 5. Возвращаем стейт в лобби
        await state.set_state(CharacterLobby.selection)
        log.info(f"Персонаж {char_id} успешно удален. UI обновлен.")

    elif callback_data.action == "delete_no":
        log.info(f"User {user.id} отменил удаление персонажа {char_id}.")

        # 1. Возвращаем стейт в лобби
        await state.set_state(CharacterLobby.selection)

        # 2. Восстанавливаем НИЖНЕЕ сообщение (message_content),
        #    показывая "Био" персонажа, как и было.
        await show_status_tab_logic(
            char_id=char_id,
            state=state,
            bot=bot,
            call=call,  # `show_status_tab_logic` сам возьмет `call.message`
            key="bio",
            session=session,
        )


@router.callback_query(InGame.navigation, LobbySelectionCallback.filter(F.action == "logout"))
async def logout_handler(call: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    """
    Обрабатывает выход из игрового мира обратно в лобби.

    Args:
        call (CallbackQuery): Входящий callback.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        session (AsyncSession): Сессия базы данных.
    """
    if not call.from_user:
        log.warning("Хэндлер 'logout_handler' получил обновление без 'from_user'.")
        return

    user = call.from_user
    log.info(f"Хэндлер 'logout_handler' [logout] вызван user_id={user.id}")
    await call.answer()

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")

    lobby_service = LobbyService(user=user, char_id=char_id, state_data=state_data)

    # 1. Получаем ID сообщений
    message_menu_data = lobby_service.get_message_menu_data()
    message_content_data = lobby_service.get_message_content_data()

    if not message_menu_data or not message_content_data:
        log.error(f"User {user.id}: Не найдены message_menu или message_content для выхода из мира.")
        await Err.generic_error(call)
        return

    menu_chat_id, menu_message_id = message_menu_data
    content_chat_id, content_message_id = message_content_data

    # 2. Удаляем нижнее сообщение (навигация)
    try:
        await bot.delete_message(chat_id=content_chat_id, message_id=content_message_id)
    except TelegramAPIError as e:
        log.warning(f"Не удалось удалить content_message при выходе: {e}")

    # 3. Редактируем верхнее сообщение в лобби
    characters = await lobby_service.get_data_characters(session)
    text, kb = lobby_service.get_data_lobby_start(characters)
    await bot.edit_message_text(chat_id=menu_chat_id, message_id=menu_message_id, text=text, reply_markup=kb)

    # 4. Сбрасываем состояние и данные FSM
    await state.set_state(CharacterLobby.selection)

    # Создаем новый, чистый session_context, сохраняя только самое необходимое
    new_session_context = {
        "user_id": user.id,
        "message_menu": message_menu_data,
        "char_id": None,
        "message_content": None,  # Явно сбрасываем, так как оно удалено
    }
    await state.set_data({FSM_CONTEXT_KEY: new_session_context})

    if characters:
        await state.update_data(characters=await fsm_store(value=characters))

    log.info(f"User {user.id} успешно вышел в лобби. FSM сброшен.")


@router.callback_query(CharacterLobby.selection, LobbySelectionCallback.filter(F.action == "login"))
async def start_logging_handler(call: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    """
    Обрабатывает нажатие кнопки "Войти в игру".
    Реализует вход или редирект в туториал в зависимости от game_stage.
    """
    if not call.from_user:
        log.warning("Хэндлер 'start_logging_handler' получил обновление без 'from_user'.")
        return

    # --- 1. Сбор данных ---
    user_id = call.from_user.id
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")

    # Нам нужны данные о сообщении, чтобы редактировать его
    message_content: dict[str, Any] | None = session_context.get("message_content")
    message_menu: dict[str, Any] | None = session_context.get("message_menu")

    if not isinstance(char_id, int) or not isinstance(message_content, dict):
        log.error(f"User {call.from_user.id} нажал 'login', но FSM неполный.")
        await Err.generic_error(call)
        return

    log.info(f"Хэндлер 'start_logging_handler' [lobby:login] вызван user_id={user_id}, char_id={char_id}")
    await call.answer()

    # --- 2. Анимация и Бизнес-логика (параллельно) ---
    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)
    login_service = LoginService(char_id=char_id, state_data=state_data)

    async def run_logic():
        return await login_service.handle_login(session=session)

    results = await asyncio.gather(
        anim_service.animate_loading(duration=2.0, text="📡 <b>Установка нейро-связи...</b>"),
        run_logic(),
    )

    login_result = results[1]

    # --- 3. Обработка РЕДИРЕКТА (Если не IN_GAME) ---
    if isinstance(login_result, str):
        game_stage = login_result
        log.info(f"Редирект логина: char_id={char_id} имеет стадию '{game_stage}'. Запуск сценария восстановления.")

        # Очищаем лишнее из FSM, оставляя ядро (user_id, char_id...)
        await fsm_clean_core_state(state=state, event_source=call)

        # 🔥 ФИКС: ОБНОВЛЕНИЕ ВЕРХНЕГО МЕНЮ ПРИ РЕДИРЕКТЕ 🔥
        # Чтобы убрать кнопку "Войти" и показать "Выйти" (Logout)
        if message_menu:
            try:
                ms = MenuService(game_stage=game_stage, state_data=await state.get_data())
                menu_text, menu_kb = ms.get_data_menu()

                await bot.edit_message_text(
                    chat_id=message_menu["chat_id"],
                    message_id=message_menu["message_id"],
                    text=menu_text,
                    reply_markup=menu_kb,
                    parse_mode="HTML",
                )
                log.debug(f"Меню обновлено под стадию '{game_stage}' при редиректе.")
            except TelegramAPIError as e:
                log.warning(f"Не удалось обновить меню при редиректе: {e}")

        # === ВЕТКА 1: ТУТОРИАЛ СТАТОВ (S.P.E.C.I.A.L.) ===
        if game_stage == GameStage.TUTORIAL_STATS:
            tut_stats_service = TutorialServiceStats(char_id=char_id)
            text, kb = tut_stats_service.get_restart_stats()

            await bot.edit_message_text(
                chat_id=message_content["chat_id"],
                message_id=message_content["message_id"],
                text=text,
                reply_markup=kb,
                parse_mode="HTML",
            )

            await state.set_state(StartTutorial.start)
            await state.update_data(bonus_dict={}, event_pool=None, sim_text_count=0)
            return

        # === ВЕТКА 2: ТУТОРИАЛ СКИЛЛОВ (ВЫБОР КЛАССА) ===
        elif game_stage == GameStage.TUTORIAL_SKILL:
            skill_choices_list: list[str] = []
            tut_skill_service = TutorialServiceSkills(skills_db=skill_choices_list)
            text_skill, kb_skill = tut_skill_service.get_start_data()

            if text_skill and kb_skill:
                await bot.edit_message_text(
                    chat_id=message_content["chat_id"],
                    message_id=message_content["message_id"],
                    text=text_skill,
                    reply_markup=kb_skill,
                    parse_mode="HTML",
                )

                await state.set_state(StartTutorial.in_skills_progres)
                await state.update_data(skill_choices_list=skill_choices_list)
            else:
                log.error(f"Не удалось получить данные старта скиллов для char_id={char_id}")
                await Err.generic_error(call)
            return

        # === ВЕТКА: CREATION ===
        elif game_stage == GameStage.CREATION:
            if not isinstance(message_menu, dict):
                await Err.generic_error(call)
                return
            await start_creation_handler(
                call=call, state=state, bot=bot, user_id=user_id, char_id=char_id, message_menu=message_menu
            )
            return

        else:
            log.warning(f"Неизвестная стадия '{game_stage}' при логине.")
            await Err.generic_error(call)
            return

    # Если пришел None или ошибка структуры
    if not isinstance(login_result, tuple):
        await Err.generic_error(call)
        return

    # --- 4. ЛОГИН УСПЕШЕН (IN_GAME) ---
    state_name, loc_id = login_result
    log.info(f"Логин для char_id={char_id} успешен. Вход в: {state_name}:{loc_id}")

    # --- 5. UI для ИГРЫ ---
    nav_service = NavigationService(char_id=char_id, state_data=state_data)
    nav_text, nav_kb = await nav_service.get_navigation_ui(state_name, loc_id)

    menu_service = MenuService(game_stage="in_game", state_data=state_data)
    menu_text, menu_kb = menu_service.get_data_menu()

    if not message_menu:
        await Err.generic_error(call)
        return

    # Обновляем ВЕРХНЕЕ (Меню)
    await bot.edit_message_text(
        chat_id=message_menu["chat_id"],
        message_id=message_menu["message_id"],
        text=menu_text,
        reply_markup=menu_kb,
        parse_mode="HTML",
    )

    # Обновляем НИЖНЕЕ (Контент/Навигация)
    await bot.edit_message_text(
        chat_id=message_content["chat_id"],
        message_id=message_content["message_id"],
        text=nav_text,
        reply_markup=nav_kb,
        parse_mode="HTML",
    )

    # --- 6. Финализация FSM ---
    await fsm_clean_core_state(state=state, event_source=call)
    await state.set_state(InGame.navigation)
    log.info(f"User {user_id} (char_id={char_id}) вошел в мир. FSM: InGame.navigation.")
