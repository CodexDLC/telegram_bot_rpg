


from aiogram.types import User

from app.resources.schemas_dto.user_dto import UserUpsertDTO
from database.repositories import get_user_repo
from database.session import get_async_session


class CommandService:

    def __init__(self, user: User) -> None:
        self.telegram_id=user.id
        self.first_name=user.first_name
        self.username=user.username
        self.last_name=user.last_name
        self.language_code=user.language_code
        self.is_premium=bool(user.is_premium)



    async def create_user_in_db(self):

        user_dto = UserUpsertDTO(
            telegram_id=self.telegram_id,
            first_name=self.first_name,
            username=self.username,
            last_name=self.last_name,
            language_code=self.language_code,
            is_premium=self.is_premium
        )

        async with get_async_session() as session:
            user_repo = get_user_repo(session)
            await user_repo.upsert_user(user_dto)
