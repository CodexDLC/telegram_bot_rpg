# app/handlers/fsn_callback/lobby_character_selection.py
import logging
from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.resources.fsm_states.states import CharacterLobby
from app.resources.keyboards.inline_kb.loggin_und_new_character import get_character_lobby_kb, get_character_data_bio
from app.services.data_loader_service import load_data_auto
from app.services.helpers_module.DTO_helper import fsm_load_auto, fsm_store
from app.services.helpers_module.ui.lobby_formatters import LobbyFormatter


log = logging.getLogger(__name__)

router = Router(name="lobby_fsm")


@router.callback_query(CharacterLobby.selection, F.data.startswith("lobby:select"))
async def select_character_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обрабатывает выбор персонажа в лобби.

    Этот обработчик отвечает за:
    - Загрузку данных о персонажах из FSM или базы данных.
    - Обновление списка персонажей с выделением выбранного.
    - Отображение или обновление подробной информации (БИО) о выбранном персонаже в отдельном сообщении.
    - Сохранение актуального состояния в FSM.
    """
    await call.answer()
    char_id = int(call.data.split(":")[-1])

    # --- 1. ЗАГРУЗКА ДАННЫХ О ПЕРСОНАЖАХ ---
    # пытаемся получить список персонажей из хранилища FSM.
    characters = await fsm_load_auto(state=state, key="characters") or None

    # --- 2. ПЕРВИЧНАЯ ЗАГРУЗКА ИЗ БД ---
    # Если в FSM данных нет (например, первый вход в лобби), загружаем их из базы данных.
    if characters is None:
        log.info("Данных 'characters' нет в FSM, загружаю из БД...")
        get_data = await load_data_auto(
            ["characters", "character_stats"],
            character_id=char_id,
            user_id=call.from_user.id
        )
        # Сохраняем полученные данные в FSM для последующих обращений.
        await state.update_data(
            characters=await fsm_store(value=get_data.get("characters")),
            character_stats=await fsm_store(value=get_data.get("character_stats"))
        )

    # --- 3. ПОЛУЧЕНИЕ АКТУАЛЬНЫХ ДАННЫХ FSM ---
    # Загружаем все данные из FSM, включая информацию о сообщениях, отправленных ранее.
    state_data = await state.get_data()
    mes_content_data = state_data.get("message_content") or {}

    # --- 4. ОБНОВЛЕНИЕ ИНТЕРФЕЙСА ---
    # Этот блок выполняется всегда, когда есть данные о персонажах.
    if characters:
        log.info(f"Ветка где characters = True. ID сообщения БИО: {mes_content_data.get('message_id')}")

        # --- 4.1. ОБНОВЛЕНИЕ СПИСКА ПЕРСОНАЖЕЙ (ВЕРХНЕЕ СООБЩЕНИЕ) ---
        # Редактируем сообщение со списком персонажей, выделяя выбранного.
        await call.message.edit_text(
            text=LobbyFormatter.format_character_list(characters),
            parse_mode='HTML',
            reply_markup=get_character_lobby_kb(characters, selected_char_id=char_id)
        )

        # Находим объект выбранного персонажа.
        char = [character for character in characters if character.character_id == char_id][0]

        # --- 5. УПРАВЛЕНИЕ СООБЩЕНИЕМ С БИО (НИЖНЕЕ СООБЩЕНИЕ) ---
        # Проверяем, было ли уже отправлено сообщение с БИО.
        if mes_content_data:
            # Если да - редактируем его, обновляя информацию.
            log.info(f"Редактируем БИО (mes_id: {mes_content_data.get('message_id')})")
            try:
                await bot.edit_message_text(
                    chat_id=mes_content_data.get("chat_id"),
                    message_id=mes_content_data.get("message_id"),
                    text=LobbyFormatter.format_character_bio(char),
                    parse_mode='HTML',
                    reply_markup=get_character_data_bio()
                )
            except Exception as e:
                # Обработка случая, если сообщение было удалено пользователем.
                log.warning(f"Не удалось отредактировать сообщение БИО: {e}. Создаю новое.")
                mes_content_data = {}  # Сбрасываем данные, чтобы создать новое сообщение.

        # --- 6. СОЗДАНИЕ НОВОГО СООБЩЕНИЯ С БИО ---
        # Если сообщения с БИО еще нет (первый клик или ошибка редактирования).
        if not mes_content_data:
            log.info(f"Создаем новое БИО")
            mes_content = await call.message.answer(
                text=LobbyFormatter.format_character_bio(char),
                parse_mode='HTML',
                reply_markup=get_character_data_bio()
            )
            # Готовим данные нового сообщения для сохранения в FSM.
            mes_content_data = {
                "message_id": mes_content.message_id,
                "chat_id": mes_content.chat.id
            }

        # --- 7. ФИНАЛЬНОЕ СОХРАНЕНИЕ СОСТОЯНИЯ ---
        # Сохраняем ID выбранного персонажа и данные о сообщении с БИО в FSM.
        await state.update_data(
            selected_char_id=char_id,
            message_content=mes_content_data,
        )

    else:
        # Обработка случая, когда у пользователя нет персонажей.
        log.warning(f"У пользователя {call.from_user.id} нет персонажей.")
        await call.message.edit_text("У вас нет созданных персонажей.")



@router.callback_query(CharacterLobby.selection, F.data.startswith("lobby:action:"))
async def start_edit_content_bio_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обрабатывает переключение между БИО и статами в подробной информации о персонаже.

    Этот обработчик вызывается кнопками "Биография" и "Статы" и обновляет
    нижнее сообщение, отображая соответствующую информацию.
    """
    log.info("Редактирование нижнего сообщения (БИО/статы)")

    await call.answer()
    # --- 1. ИЗВЛЕЧЕНИЕ ДАННЫХ ---
    type_action = call.data.split(":")[-1]  # "bio" или "stats"
    state_data = await state.get_data()
    message_content = state_data.get("message_content")
    char_id = state_data.get("selected_char_id")
    bd_data_by_id = state_data.get("bd_data_by_id") or {}

    # --- 2. ЗАГРУЗКА ДАННЫХ ИЗ БД (ЕСЛИ НЕОБХОДИМО) ---
    # Если данных по конкретному персонажу еще нет в FSM, загружаем их.
    if not bd_data_by_id or bd_data_by_id.get("id") != char_id:
        log.info(f"Данные для char_id={char_id} отсутствуют или неактуальны в FSM, загружаю из БД.")
        get_data = await load_data_auto(
            ["character", "character_stats"],
            character_id=char_id,
            user_id=call.from_user.id
        )
        character = await fsm_store(value=get_data.get("character"))
        character_stats = await fsm_store(value=get_data.get("character_stats"))

        log.debug(f"""
            2. ЗАГРУЗКА ДАННЫХ ИЗ БД (ЕСЛИ НЕОБХОДИМО)
            character: {character}
            character_stats: {character_stats}

        """)

        # Формируем и сохраняем пакет данных по персонажу.
        bd_data_by_id = {
            "id": char_id,
            "character": character,
            "character_stats": character_stats
        }
        await state.update_data(bd_data_by_id=bd_data_by_id)

    # --- 3. ПОЛУЧЕНИЕ АКТУАЛЬНЫХ ДАННЫХ ИЗ FSM ---
    state_data = await state.get_data()
    bd_data_by_id = state_data.get("bd_data_by_id")
    character = bd_data_by_id.get("character")
    character_stats = bd_data_by_id.get("character_stats")

    # --- 4. ОБНОВЛЕНИЕ СООБЩЕНИЯ В ЗАВИСИМОСТИ ОТ ДЕЙСТВИЯ ---
    try:
        if type_action == "bio":
            # Показываем биографию
            await bot.edit_message_text(
                chat_id=message_content.get("chat_id"),
                message_id=message_content.get("message_id"),
                text=LobbyFormatter.format_character_bio(character),
                parse_mode='HTML',
                reply_markup=get_character_data_bio()
            )

        elif type_action == "stats":
            # Показываем характеристики
            await bot.edit_message_text(
                chat_id=message_content.get("chat_id"),
                message_id=message_content.get("message_id"),
                text=LobbyFormatter.format_character_stats(character_stats),
                parse_mode='HTML',
                reply_markup=get_character_data_bio()
            )

    except TelegramBadRequest as e:
        # Игнорируем ошибку, если пытаемся отправить тот же самый текст.
        if "message is not modified" in str(e):
            log.debug("Сообщение не изменилось, игнорируем.")
        else:
            log.warning(f"Неожиданная ошибка Telegram API: {e}")
    except Exception as e:
        log.exception(f"Критическая ошибка при обновлении БИО/Статов: {e}")


@router.callback_query(CharacterLobby.start_logging, F.data=="lobby:login")
async def start_logging_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обрабатывает нажатие кнопки "Войти в игру".

    На данный момент является заглушкой. В будущем здесь будет реализована
    логика входа персонажа в игровой мир, включая проверку туториалов и
    загрузку соответствующего игрового состояния.
    """
    await call.answer()
    state_data = await state.get_data()
    message_content = state_data.get("message_content")
    message_menu = state_data.get("message_menu")
    char_id = state_data.get("selected_char_id")

    # TODO: Реализовать полную логику входа в игру.
    # TODO: Реализовать систему сохранения прогресса туториала,
    # чтобы возвращать игрока на нужный этап после пересоздания или логина.
    
    # --- ЗАГЛУШКА: ИНФОРМИРОВАНИЕ О НЕРАБОТАЮЩЕЙ ФУНКЦИИ ---
    # Редактируем оба сообщения (меню и контент), чтобы показать, что функция в разработке.
    await bot.edit_message_text(
        chat_id=message_menu.get("chat_id"),
        message_id=message_menu.get("message_id"),
        text="Логина в игру пока нету",
        parse_mode='HTML',
        reply_markup=None
    )

    await bot.edit_message_text(
        chat_id=message_content.get("chat_id"),
        message_id=message_content.get("message_id"),
        text=" Логина в игру пока нету",
        parse_mode='HTML',
        reply_markup=None

    )

    log.debug(f"Состояние FSM при попытке логина: {state_data}")
