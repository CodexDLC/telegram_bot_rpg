from apps.common.services.core_service.redis_key import RedisKeys as Rk
from apps.common.services.core_service.redis_service import RedisService


class AccountManager:
    """
    Менеджер для управления данными аккаунтов персонажей в Redis.

    Предоставляет методы для создания, получения, обновления и проверки
    существования данных аккаунта, используя хеши Redis с ключом 'ac:{char_id}'.
    """

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service

    async def create_account(self, char_id: int, data: dict) -> None:
        """
        Создает или полностью перезаписывает хеш аккаунта для указанного персонажа.

        Args:
            char_id: Уникальный идентификатор персонажа.
            data: Словарь данных для сохранения в хеше аккаунта.
        """
        key = Rk.get_account_key(char_id)
        await self.redis_service.set_hash_fields(key, data)

    async def get_account_data(self, char_id: int) -> dict[str, str] | None:
        """
        Получает все поля и их значения из хеша аккаунта для указанного персонажа.

        Args:
            char_id: Уникальный идентификатор персонажа.

        Returns:
            Словарь, содержащий все данные аккаунта, или None, если хеш не найден.
        """
        key = Rk.get_account_key(char_id)
        return await self.redis_service.get_all_hash(key)

    async def update_account_fields(self, char_id: int, data: dict) -> None:
        """
        Обновляет только указанные поля в хеше аккаунта для персонажа.

        Если поле не существует, оно будет создано. Существующие поля будут перезаписаны.

        Args:
            char_id: Уникальный идентификатор персонажа.
            data: Словарь с полями и их новыми значениями для обновления.
        """
        key = Rk.get_account_key(char_id)
        await self.redis_service.set_hash_fields(key, data)

    async def get_account_field(self, char_id: int, field: str) -> str | None:
        """
        Получает значение конкретного поля из хеша аккаунта персонажа.

        Args:
            char_id: Уникальный идентификатор персонажа.
            field: Имя поля, значение которого нужно получить.

        Returns:
            Строковое значение поля, если найдено, иначе None.
        """
        key = Rk.get_account_key(char_id)
        return await self.redis_service.get_hash_field(key, field)

    async def account_exists(self, char_id: int) -> bool:
        """
        Проверяет существование хеша аккаунта для указанного персонажа.

        Args:
            char_id: Уникальный идентификатор персонажа.

        Returns:
            True, если хеш аккаунта существует, иначе False.
        """
        key = Rk.get_account_key(char_id)
        return await self.redis_service.key_exists(key)
