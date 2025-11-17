# app/services/core_service/managers/account_manager.py
from app.services.core_service.redis_service import redis_service
from app.services.core_service.redis_key import RedisKeys as RKB

class AccountManager:
    """
    CRUD-Менеджер (Репозиторий) для ключей 'ac:<char_id>'.
    """

    async def create_account(self, char_id: int, data: dict) -> None:
        """Создает или ПОЛНОСТЬЮ перезаписывает хеш 'ac:<char_id>'."""
        key = RKB.get_account_key(char_id)
        await redis_service.set_hash_fields(key, data)

    async def get_account_data(self, char_id: int) -> dict[str, str] | None:
        """Получает *все* данные из хеша 'ac:<char_id>'."""
        key = RKB.get_account_key(char_id)
        return await redis_service.get_all_hash(key)

    async def update_account_fields(self, char_id: int, data: dict) -> None:
        """Обновляет *только* указанные поля в хеше 'ac:<char_id>'."""
        key = RKB.get_account_key(char_id)
        await redis_service.set_hash_fields(key, data)


    async def get_account_field(self, char_id: int, field: str) -> str | None:
        """Получает *одно* поле из хеша 'ac:<char_id>'."""
        key = RKB.get_account_key(char_id)
        return await redis_service.get_hash_field(key, field)


    async def account_exists(self, char_id: int) -> bool:
        """Проверяет, существует ли ключ 'ac:<char_id>'."""
        key = RKB.get_account_key(char_id)
        return await redis_service.key_exists(key)


account_manager = AccountManager()