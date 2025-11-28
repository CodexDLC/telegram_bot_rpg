# app/handlers/callback/game/arena.py
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import InGame
from app.services.game_service.arena_service import ArenaService
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.combat.combat_ui_service import CombatUIService


async def start_arena_combat(
    user_id: int,
    char_id: int,
    bot: Bot,
    state: FSMContext,
    session: AsyncSession,
    # Мы передаем call для обработки ошибок, если нужно,
    # или просто chat_id/message_id для рендера
    message_menu: dict,
    message_content: dict,
) -> None:
    """
    Инициализирует бой, обновляет FSM и рендерит интерфейс боя.
    Вызывается из диспетчера меню.
    """
    log.info(f"Запуск логики Арены для char_id={char_id}")

    # 1. Сервис Арены: Создаем бой (Манекен)
    arena_service = ArenaService(session, char_id)
    session_id = await arena_service.start_training_dummy()

    if not session_id:
        log.error(f"Не удалось создать бой для char_id={char_id}")
        # Тут можно отправить уведомление об ошибке, если нужно
        return

    # 2. Переводим FSM в состояние БОЯ
    await state.set_state(InGame.combat)

    # 3. Сохраняем ID сессии боя в контекст
    # Нам нужно обновить данные в state
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    session_context["combat_session_id"] = session_id

    # Обновляем state_data с новым session_id, чтобы CombatUIService его увидел
    # ВАЖНО: Мы обновляем словарь внутри DTO (или dict),
    # но лучше обновить весь ключ через update_data
    await state.update_data({FSM_CONTEXT_KEY: session_context})

    # Обновляем локальную переменную state_data для передачи в сервис
    state_data[FSM_CONTEXT_KEY] = session_context

    # 4. Инициализируем UI Боя
    ui_service = CombatUIService(user_id, char_id, session_id, state_data)

    # А. Получаем Лог (Верх)
    log_text, log_kb = await ui_service.render_combat_log(page=0)

    # Б. Получаем Пульт (Низ)
    dash_text, dash_kb = await ui_service.render_dashboard(current_selection={})

    # 5. Обновляем сообщения
    # Верхнее (Лог)
    if message_menu:
        await bot.edit_message_text(
            chat_id=message_menu["chat_id"],
            message_id=message_menu["message_id"],
            text=log_text,
            reply_markup=log_kb,
            parse_mode="HTML",
        )

    # Нижнее (Пульт)
    if message_content:
        await bot.edit_message_text(
            chat_id=message_content["chat_id"],
            message_id=message_content["message_id"],
            text=dash_text,
            reply_markup=dash_kb,
            parse_mode="HTML",
        )
