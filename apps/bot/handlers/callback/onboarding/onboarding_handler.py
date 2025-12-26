from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.callback_data import OnboardingCallback
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY, fsm_load_auto, fsm_store
from apps.common.core.container import AppContainer
from apps.common.schemas_dto import SessionDataDTO
from apps.common.services.validators.character_validator import validate_character_name

router = Router(name="onboarding_router")

# --- Handlers ---


@router.callback_query(OnboardingCallback.filter())
async def on_onboarding_action(
    call: CallbackQuery,
    callback_data: OnboardingCallback,
    state: FSMContext,
    session: AsyncSession,
    container: AppContainer,
):
    """
    Обработка нажатий кнопок в процессе онбординга.
    """
    orchestrator = container.get_onboarding_bot_orchestrator(session)

    # Получаем данные из FSM
    fsm_data = await state.get_data()
    char_id = fsm_data.get("char_id")

    if not char_id:
        await call.answer("Ошибка: Персонаж не найден.", show_alert=True)
        return

    # Если это выбор гендера, сохраняем его в FSM сразу
    if callback_data.action == "set_gender":
        await state.update_data(gender=callback_data.value)
        # Обновляем локальную копию для передачи в оркестратор
        fsm_data["gender"] = callback_data.value

    # Вызываем оркестратор
    view_dto = await orchestrator.handle_request(
        char_id=char_id, action=callback_data.action, value=callback_data.value, fsm_data=fsm_data
    )

    # Если это была финализация, обновляем SessionDataDTO
    if callback_data.action == "finalize":
        try:
            session_data: SessionDataDTO | None = await fsm_load_auto(state, FSM_CONTEXT_KEY)
            if session_data:
                session_data.char_id = char_id
                # Также можно сохранить имя, если оно есть в fsm_data
                if "name" in fsm_data:
                    session_data.char_name = fsm_data["name"]

                await state.update_data({FSM_CONTEXT_KEY: await fsm_store(session_data)})
        except Exception as e:  # noqa: BLE001
            log.warning(f"Failed to finalize onboarding session data: {e}", exc_info=True)

    # Обновляем сообщение
    if call.message:
        try:
            # mypy жалуется на InaccessibleMessage, но мы проверяем call.message
            # и в большинстве случаев это Message.
            await call.message.edit_text(text=view_dto.text, reply_markup=view_dto.keyboard)  # type: ignore
        except TelegramAPIError:
            await call.answer()
    else:
        await call.answer("Ошибка: Сообщение не найдено.")


@router.message(InGame.onboarding)
async def on_name_input(message: Message, state: FSMContext, session: AsyncSession, container: AppContainer, bot: Bot):
    """
    Обработка ввода имени (текстовое сообщение).
    """
    # 1. Удаляем сообщение пользователя (чистильщик)
    try:
        await message.delete()
    except TelegramAPIError:
        log.warning(f"Failed to delete user message: {message.message_id}")

    orchestrator = container.get_onboarding_bot_orchestrator(session)

    fsm_data = await state.get_data()
    char_id = fsm_data.get("char_id")
    session_context = fsm_data.get(FSM_CONTEXT_KEY, {})
    message_content = session_context.get("message_content")

    # Вспомогательная функция для отправки ошибок (редактируем контекстное сообщение)
    async def send_error(text: str):
        if message_content and "chat_id" in message_content and "message_id" in message_content:
            try:
                await bot.edit_message_text(
                    chat_id=message_content["chat_id"],
                    message_id=message_content["message_id"],
                    text=text,
                )
            except TelegramAPIError:
                await message.answer(text)
        else:
            await message.answer(text)

    if not char_id:
        await send_error("Ошибка сессии. Попробуйте /start")
        return

    if not message.text:
        await send_error("Пожалуйста, введите имя текстом.")
        return

    name = message.text.strip()

    # Валидация имени
    is_valid, error_msg = validate_character_name(name)
    if not is_valid:
        await send_error(f"⚠️ {error_msg}")
        return

    # Сохраняем имя в FSM
    await state.update_data(name=name)
    fsm_data["name"] = name

    # Вызываем оркестратор с действием set_name
    view_dto = await orchestrator.handle_request(char_id=char_id, action="set_name", value=name, fsm_data=fsm_data)

    # Отправляем новое сообщение (редактируем старое)
    if message_content and "chat_id" in message_content and "message_id" in message_content:
        try:
            await bot.edit_message_text(
                chat_id=message_content["chat_id"],
                message_id=message_content["message_id"],
                text=view_dto.text,
                reply_markup=view_dto.keyboard,
            )
        except TelegramAPIError:
            # Если не удалось отредактировать, шлем новое
            sent_msg = await message.answer(text=view_dto.text, reply_markup=view_dto.keyboard)
            # Обновляем координаты, если пришлось отправить новое
            session_context["message_content"] = {
                "chat_id": sent_msg.chat.id,
                "message_id": sent_msg.message_id,
            }
            await state.update_data({FSM_CONTEXT_KEY: session_context})
    else:
        sent_msg = await message.answer(text=view_dto.text, reply_markup=view_dto.keyboard)
        # Обновляем координаты
        session_context["message_content"] = {
            "chat_id": sent_msg.chat.id,
            "message_id": sent_msg.message_id,
        }
        await state.update_data({FSM_CONTEXT_KEY: session_context})


# --- Entry Point ---
async def start_onboarding_process(
    bot: Bot,
    state: FSMContext,
    char_id: int,
    session: AsyncSession,
    container: AppContainer,
    message: Message | None = None,
):
    """
    Запускает процесс онбординга для указанного персонажа.
    Редактирует нижнее сообщение (контекст), если оно есть в FSM.
    """
    await state.set_state(InGame.onboarding)
    await state.update_data(char_id=char_id)

    orchestrator = container.get_onboarding_bot_orchestrator(session)
    view_dto = await orchestrator.handle_request(char_id=char_id, action="start")

    # Пытаемся найти координаты нижнего сообщения
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content = session_context.get("message_content")

    if message_content and "chat_id" in message_content and "message_id" in message_content:
        try:
            await bot.edit_message_text(
                chat_id=message_content["chat_id"],
                message_id=message_content["message_id"],
                text=view_dto.text,
                reply_markup=view_dto.keyboard,
            )
            return
        except TelegramAPIError:
            log.warning("Failed to edit content message for onboarding, sending new one.")

    # Если не нашли или не смогли отредактировать - шлем новое (если есть message)
    if message:
        sent_msg = await message.answer(text=view_dto.text, reply_markup=view_dto.keyboard)
        # Сохраняем новые координаты
        session_context["message_content"] = {
            "chat_id": sent_msg.chat.id,
            "message_id": sent_msg.message_id,
        }
        await state.update_data({FSM_CONTEXT_KEY: session_context})
