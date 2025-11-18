# app/services/ui_service/navigation_service.py
from typing import Any

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

# TODO: В будущем здесь будет `game_dungeon_service`
# --- Импорты Уровня 2 (Репозитории/Менеджеры) ---
from app.services.core_service.manager.account_manager import account_manager
from app.services.core_service.manager.world_manager import world_manager

# --- Импорты Уровня 3 (Бизнес-Логика) ---
from app.services.game_service.game_world_service import game_world_service

# --- Импорты Уровня 1 (Инструменты) ---
# TODO: нужно создать NavigationCallback в 'app/resources/keyboards/callback_data.py'
# from app.resources.keyboards.callback_data import NavigationCallback


class NavigationService:
    """
    Сервис-Оркестратор для Навигации.

    Отвечает за:
    1. Формирование UI (текст/кнопки) для локаций/данжей.
    2. Обработку перемещения игрока (логика `move_player`).
    """

    def __init__(self, char_id: int, state_data: dict[str, Any]):
        self.char_id = char_id
        self.state_data = state_data
        log.debug(f"Инициализирован NavigationService для char_id={self.char_id}")

    # --- 1. Метод для UI (Вызывается Хэндлером Логина) ---

    async def get_navigation_ui(self, state: str, loc_id: str) -> tuple[str, InlineKeyboardMarkup | None]:
        """
        Главный метод для получения UI.
        Вызывает приватный метод в зависимости от 'state'.
        """
        log.debug(f"get_navigation_ui: char_id={self.char_id}, state={state}, loc_id={loc_id}")

        if state == "world":
            # --- ВЫПОЛНЯЕМ БИЗНЕС-ЛОГИКУ (как мы и решили) ---
            # При входе в мир мы добавляем игрока в Set
            await world_manager.add_player_to_location(loc_id, self.char_id)
            log.info(f"Игрок {self.char_id} добавлен в 'world:players_loc:{loc_id}'")

            return await self._get_world_location_ui(loc_id)

        elif state == "s_d":
            # TODO: Реализовать логику добавления игрока в 's_d' (если она нужна)
            return await self._get_solo_dungeon_ui(loc_id)

        else:
            log.error(f"Неизвестный state '{state}' для char_id={self.char_id}")
            return "Ты находишься в пустоте. (Ошибка state)", None

    # --- 2. Метод для Логики Перемещения (Вызывается Хэндлером Навигации) ---

    async def move_player(self, target_loc_id: str) -> tuple[str, InlineKeyboardMarkup | None] | None:
        """
        Главный метод для ПЕРЕМЕЩЕНИЯ.
        Вызывает приватный метод в зависимости от 'state'.
        """

        # 1. Получить текущее состояние (state, loc_id) из `ac:char_id`
        current_data = await account_manager.get_account_data(self.char_id)
        if not current_data:
            log.error(f"Не удалось найти ac: FSM для char_id={self.char_id} при перемещении.")
            return None

        current_state = current_data.get("state")

        # 2. Вызвать нужный приватный обработчик
        if current_state == "world":
            return await self._move_in_world(current_data, target_loc_id)
        elif current_state == "s_d":
            # TODO: Реализовать `_move_in_dungeon(current_data, target_loc_id)`
            pass

        return None

    # --- 3. Приватные методы (Генераторы UI) ---

    async def _get_world_location_ui(self, loc_id: str) -> tuple[str, InlineKeyboardMarkup | None]:
        """Формирует UI для МИРОВОЙ локации."""

        # 1. Получаем "умные" данные
        nav_data = await game_world_service.get_location_for_navigation(loc_id)
        if not nav_data:
            return "Ошибка: Локация не найдена.", None

        # 2. Формируем Текст
        text = f"<b>{nav_data.get('name')}</b>\n\n{nav_data.get('description')}"

        # 3. Добавляем "социальную" информацию
        players_set = await world_manager.get_players_in_location(loc_id)
        players_set.discard(str(self.char_id))  # Убираем себя

        if players_set:
            text += f"\n\n<i>Здесь также: {len(players_set)} (в будущем их имена)</i>"

        # TODO: Добавить логику отображения NPC
        # npc_list = json.loads(nav_data.get("npc_list", "[]"))
        # if npc_list:
        #    text += f"\n\n<i>Вы видите: ... (имена NPC)</i>"

        # 4. Формируем Клавиатуру
        kb = InlineKeyboardBuilder()
        exits_dict = nav_data.get("exits", {})
        if isinstance(exits_dict, dict):
            for _target_id, exit_data in exits_dict.items():
                if isinstance(exit_data, dict):
                    exit_data.get("text_button", "???")

                    # TODO: Заменить 'pass' на реальный NavigationCallback
                    # kb.button(text=button_text, callback_data=NavigationCallback(
                    #    action="move",
                    #    target_id=target_id
                    # ).pack())
                    pass

        kb.adjust(1)
        return text, kb.as_markup()

    async def _get_solo_dungeon_ui(self, instance_id: str) -> tuple[str, InlineKeyboardMarkup | None]:
        """Формирует UI для СОЛО-ДАНЖА."""

        # TODO: Реализовать логику генерации UI для соло-данжа
        # 1. `dungeon_data = await dungeon_manager.get_solo_dungeon(instance_id)`
        # 2. `room_data = await dungeon_template_service.get_room(dungeon_data["room_id"])`
        # 3. Собрать UI...
        return f"ЗАГЛУШКА: Вы в соло-данже {instance_id}", None

    # --- 4. Приватные методы (Логика Перемещения) ---

    async def _move_in_world(
        self, current_data: dict[str, Any], target_loc_id: str
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Обрабатывает перемещение между МИРОВЫМИ локациями."""

        current_loc_id = current_data.get("location_id")
        if not isinstance(current_loc_id, str):
            log.error(f"current_loc_id не является строкой для char_id={self.char_id}")
            return "Ошибка: текущая локация не найдена.", None

        # 1. Убираем игрока со старого места
        await world_manager.remove_player_from_location(current_loc_id, self.char_id)

        # 2. Добавляем на новое
        await world_manager.add_player_to_location(target_loc_id, self.char_id)

        # 3. Обновляем "сохранение" игрока в `ac:char_id`
        await account_manager.update_account_fields(
            self.char_id,
            {
                "location_id": target_loc_id,
                "prev_location_id": current_loc_id,
                "state": "world",  # (Остаемся в том же стейте)
                "prev_state": current_data.get("state", "world"),
            },
        )

        # 4. Возвращаем UI *новой* локации
        return await self._get_world_location_ui(target_loc_id)
