from aiogram import Router
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

router = Router()

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
async def on_name_input(message: Message, state: FSMContext, session: AsyncSession, container: AppContainer):
    """
    Обработка ввода имени (текстовое сообщение).
    """
    orchestrator = container.get_onboarding_bot_orchestrator(session)

    fsm_data = await state.get_data()
    char_id = fsm_data.get("char_id")

    if not char_id:
        await message.answer("Ошибка сессии. Попробуйте /start")
        return

    if not message.text:
        await message.answer("Пожалуйста, введите имя текстом.")
        return

    name = message.text.strip()

    # Валидация имени
    is_valid, error_msg = validate_character_name(name)
    if not is_valid:
        await message.answer(f"⚠️ {error_msg}")
        return

    # Сохраняем имя в FSM
    await state.update_data(name=name)
    fsm_data["name"] = name

    # Вызываем оркестратор с действием set_name
    view_dto = await orchestrator.handle_request(char_id=char_id, action="set_name", value=name, fsm_data=fsm_data)

    # Отправляем новое сообщение
    await message.answer(text=view_dto.text, reply_markup=view_dto.keyboard)


# --- Entry Point ---
async def start_onboarding_process(
    message: Message, state: FSMContext, char_id: int, session: AsyncSession, container: AppContainer
):
    """
    Запускает процесс онбординга для указанного персонажа.
    """
    await state.set_state(InGame.onboarding)
    await state.update_data(char_id=char_id)

    orchestrator = container.get_onboarding_bot_orchestrator(session)

    view_dto = await orchestrator.handle_request(char_id=char_id, action="start")

    await message.answer(text=view_dto.text, reply_markup=view_dto.keyboard)
