# app/handlers/fsn_callback/lobby_character_selection.py
import logging
from aiogram import Router, F, Bot

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
    Обрабатывает выбор персонажа.
    """
    await call.answer()
    char_id = int(call.data.split(":")[-1])

    # 1. ЗАГРУЖАЕМ ДАННЫЕ ИЗ FSM
    characters = await fsm_load_auto(state=state, key="characters") or None

    # 2. ЕСЛИ В FSM ПУСТО (ПЕРВЫЙ КЛИК) - ГРУЗИМ ИЗ БД И СРАЗУ СОХРАНЯЕМ В FSM
    if characters is None:
        log.info("Данных 'characters' нет в FSM, загружаю из БД...")
        get_data = await load_data_auto(
            ["characters", "characters_stats"],
            character_id=char_id,
            user_id=call.from_user.id
        )
        # Сразу сохраняем в FSM и перезаписываем локальные переменные
        characters = await fsm_store(value=get_data.get("characters"))
        characters_stats = await fsm_store(value=get_data.get("characters_stats"))
        await state.update_data(characters=characters, characters_stats=characters_stats)

    # 3. ПОЛУЧАЕМ АКТУАЛЬНЫЕ ДАННЫЕ FSM (включая message_content от *прошлых* кликов)
    state_data = await state.get_data()
    mes_content_data = state_data.get("message_content") or {}


    # 4. ТЕПЕРЬ 'if characters' СРАБОТАЕТ ДАЖЕ ПРИ ПЕРВОМ КЛИКЕ
    if characters:
        log.info(f"Ветка где characters = True. ID сообщения БИО: {mes_content_data.get('message_id')}")

        # Обновляем ВЕРХНЕЕ сообщение (список персонажей)
        await call.message.edit_text(
            text=LobbyFormatter.format_character_list(characters),
            parse_mode='HTML',
            reply_markup=get_character_lobby_kb(characters, selected_char_id=char_id)
        )

        char = [character for character in characters if character.character_id == char_id][0]

        # 5. ПРОВЕРЯЕМ, ЕСТЬ ЛИ У НАС УЖЕ НИЖНЕЕ СООБЩЕНИЕ
        if mes_content_data:
            # Если да - редактируем его
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
                # На случай, если сообщение было удалено (редко, но бывает)
                log.warning(f"Не удалось отредактировать сообщение БИО: {e}. Создаю новое.")
                mes_content_data = {}  # Сбрасываем, чтобы создать новое

        # 6. ЕСЛИ НИЖНЕГО СООБЩЕНИЯ НЕТ (первый клик или ошибка выше)
        if not mes_content_data:
            log.info(f"Создаем новое БИО")
            mes_content = await call.message.answer(
                text=LobbyFormatter.format_character_bio(char),
                parse_mode='HTML',
                reply_markup=get_character_data_bio()
            )
            # Готовим данные нового сообщения к сохранению
            mes_content_data = {
                "message_id": mes_content.message_id,
                "chat_id": mes_content.chat.id
            }

        # 7. ФИНАЛЬНОЕ СОХРАНЕНИЕ ВСЕХ ДАННЫХ В FSM
        await state.update_data(
            selected_char_id=char_id,
            message_content=mes_content_data,
        )

    else:
        # Сюда код попадет, если у пользователя ВООБЩЕ нет персонажей
        log.warning(f"У пользователя {call.from_user.id} нет персонажей.")
        await call.message.edit_text("У вас нет созданных персонажей.")



@router.callback_query(CharacterLobby.selection, F.data.startswith("lobby:action:"))
async def start_edit_content_bio_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
         Редактирование нижнего сообщения при проверках разных данных персонажа
    """
    log.info("Редактирование нижнего сообщения при проверках разных данных персонажа")

    await call.answer()
    type_action = call.data.split(":")[-1]
    state_data = await state.get_data()
    message_content = state_data.get("message_content")
    char_id = state_data.get("selected_char_id")
    bd_data_by_id = state_data.get("bd_data_by_id") or {}

    if bd_data_by_id:
        log.info(f"Ветка когда bd_data_by_id None")
        get_data = await load_data_auto(
            ["character", "characters_stats"],
            character_id =char_id,
            user_id = call.from_user.id
        )
        character = await fsm_store(value=get_data.get("character"))
        characters_stats = await fsm_store(value=get_data.get("characters_stats"))

        log.debug(f"""
        --------------
        Данные после загрузки из бд
        --------------
        {character}
        --------------
        {characters_stats}     

        """
        )

        bd_data_by_id = {
                "id": char_id,
                "character": character,
                "characters_stats" : characters_stats

        }
        await state.update_data(bd_data_by_id=bd_data_by_id)


    state_data = await state.get_data()
    bd_data_by_id = state_data.get("bd_data_by_id")
    character = bd_data_by_id.get("character")
    characters_stats = bd_data_by_id.get("characters_stats")

    log.debug(
        f"""
        ===========================
        {bd_data_by_id}
  
        ---------------------------
        
        {character} {type(character)}
            
        ---------------------------
        {characters_stats}  {type(characters_stats)}     
        
        ===========================
        
        """
    )

    if type_action == "bio":

        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=LobbyFormatter.format_character_bio(character),
            parse_mode='HTML',
            reply_markup=get_character_data_bio()
        )

    elif type_action == "stats":

        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=LobbyFormatter.format_character_stats(characters_stats),
            parse_mode='HTML',
            reply_markup=get_character_data_bio()
        )

    await state.update_data()




@router.callback_query(CharacterLobby.start_logging, F.data=="lobby:action:login")
async def start_logging_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Инициация логина персонажа в игру подготовка меню с кнопками и редактирования контент меню в режиме путешествия.
    """
    await call.answer()
    state_data = await state.get_data()
    message_content = state_data.get("message_content")
    message_menu = state_data.get("message_menu")
    char_id = state_data.get("selected_char_id")

    await bot.edit_message_text(
        chat_id=message_menu.get("chat_id"),
        message_id=message_menu.get("message_id"),
        text="",
        parse_mode='HTML',
        reply_markup=None
    )

    await bot.edit_message_text(
        chat_id=message_content.get("chat_id"),
        message_id=message_content.get("message_id"),
        text="",
        parse_mode='HTML',
        reply_markup=None

    )

    log.debug(f"{state_data}")