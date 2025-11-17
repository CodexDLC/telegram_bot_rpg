# app/services/game_service/login_service.py
class LoginService:
    """Сервис для входа персонажа в игровой мир"""

    def __init__(self, char_id: int, state_data: dict):
        self.char_id = char_id
        self.state_data = state_data

    async def check_game_stage(self) -> str:
        """
        Проверяет game_stage персонажа.
        Возвращает: "in_game" | "tutorial_stats" | "tutorial_skill" | "creation"
        """
        # Твоя задача: Написать запрос к БД (через CharactersRepoORM)
        # Подсказка: get_character(char_id) → CharacterReadDTO → .game_stage
        pass

    async def get_start_location_id(self) -> int:
        """
        Возвращает ID стартовой локации для персонажа.
        Если персонаж уже был в игре → возвращает current_location_id.
        Если первый вход → возвращает дефолтную локацию (например, 1).
        """
        # Твоя задача: Решить, откуда брать location_id
        pass

    def get_login_ui_data(self, location_id: int) -> tuple[str, InlineKeyboardMarkup]:
        """
        Формирует текст и клавиатуру для ПЕРВОГО сообщения после логина.
        """
        # Твоя задача: Сформировать текст (например, "Вы находитесь в...")
        # и клавиатуру (кнопки для навигации, если есть выходы)
        pass