# app/services/game_service/navigation_service.py
from loguru import logger as log
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.core_service.manager.account_manager import account_manager
from app.services.core_service.manager.world_manager import world_manager
# --- Импорты Уровня 3 (Бизнес-Логика) ---
from app.services.game_service.game_world_service import game_world_service
# (Тут будет `game_dungeon_service` в будущем)

# --- Импорты Уровня 2 (Репозитории/Менеджеры) ---



class NavigationService:
    """
    Сервис-Оркестратор для Навигации.

    Отвечает за:
    1. Формирование UI (текст/кнопки) для локаций/данжей.
    2. Обработку перемещения игрока (логика `move_player`).
    """

    def __init__(self, char_id: int, state_data: dict):
        self.char_id = char_id
        self.state_data = state_data
        log.debug(f"Инициализирован NavigationService для char_id={self.char_id}")

    # --- 1. Метод для UI (то, что ты просил) ---

    async def get_navigation_ui(self, state: str, loc_id: str) -> tuple[str, InlineKeyboardMarkup]:
        """
        Главный метод для получения UI.
        Вызывает приватный метод в зависимости от 'state'.
        """
        if state == "world":
            return await self._get_world_location_ui(loc_id)
        elif state == "s_d":
            return await self._get_solo_dungeon_ui(loc_id)
        else:
            log.error(f"Неизвестный state '{state}' для char_id={self.char_id}")
            return "Ты находишься в пустоте. (Ошибка state)", None

    # --- 2. Метод для Логики Перемещения (то, что ты просил) ---

    async def move_player(self, target_loc_id: str) -> tuple[str, InlineKeyboardMarkup] | None:
        """
        Главный метод для ПЕРЕМЕЩЕНИЯ.
        Вызывает приватный метод в зависимости от 'state'.
        """
        # 1. Получить текущее состояние (state, loc_id) из `ac:char_id`
        # (Твоя логика: `current_data = await account_manager.get_account_data(self.char_id)`)
        pass

        # 2. Вызвать нужный приватный обработчик
        # if current_data.get("state") == "world":
        #    return await self._move_in_world(current_data, target_loc_id)
        pass

    # --- 3. Приватные методы (твоя идея) ---

    async def _get_world_location_ui(self, loc_id: str) -> tuple[str, InlineKeyboardMarkup]:
        """Формирует UI для МИРОВОЙ локации."""

        # 1. Получаем "умные" данные
        nav_data = await game_world_service.get_location_for_navigation(loc_id)
        if not nav_data:
            return "Ошибка: Локация не найдена.", None

        # 2. Формируем Текст
        text = f"<b>{nav_data.get('name')}</b>\n\n{nav_data.get('description')}"

        # (Тут же можно добавить: "Здесь также: ... N игроков")
        # (Твоя логика: `players_set = await world_manager.get_players_in_location(loc_id)`)
        pass

        # 3. Формируем Клавиатуру
        kb = InlineKeyboardBuilder()
        exits_dict = nav_data.get("exits", {})

        for target_id, exit_data in exits_dict.items():
            button_text = exit_data.get("text_button", "???")
            # (Твоя логика: `kb.button(text=button_text, callback_data=...)`
            #  ...используя *новый* NavigationCallbackData)
            pass

        return text, kb.as_markup()

    async def _get_solo_dungeon_ui(self, instance_id: str) -> tuple[str, InlineKeyboardMarkup]:
        """Формирует UI для СОЛО-ДАНЖА."""
        # (Твоя логика в будущем:
        # 1. `dungeon_data = await dungeon_manager.get_solo_dungeon(instance_id)`
        # 2. `room_data = await dungeon_template_service.get_room(dungeon_data["room_id"])`
        # 3. Собрать UI...)
        pass

    async def _move_in_world(self, current_data: dict, target_loc_id: str) -> tuple[str, InlineKeyboardMarkup]:
        """Обрабатывает перемещение между МИРОВЫМИ локациями."""

        current_loc_id = current_data.get("location_id")

        # 1. Убираем игрока со старого места
        await world_manager.remove_player_from_location(current_loc_id, self.char_id)

        # 2. Добавляем на новое
        await world_manager.add_player_to_location(target_loc_id, self.char_id)

        # 3. Обновляем "сохранение" игрока в `ac:char_id`
        await account_manager.update_account_fields(self.char_id, {
            "location_id": target_loc_id,
            "prev_location_id": current_loc_id,
            "state": "world",  # (Остаемся в том же стейте)
            "prev_state": current_data.get("state", "world")
        })

        # 4. Возвращаем UI *новой* локации
        return await self._get_world_location_ui(target_loc_id)