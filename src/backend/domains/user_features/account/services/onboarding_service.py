from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.exceptions import SessionExpiredException
from src.backend.database.postgres.repositories.characters_repo_orm import CharactersRepoORM
from src.backend.domains.user_features.account.data.locales.onboarding_resources import OnboardingResources
from src.backend.domains.user_features.account.services.account_session_service import AccountSessionService
from src.shared.enums.domain_enums import CoreDomain
from src.shared.enums.onboarding_enums import OnboardingStepEnum
from src.shared.schemas.character import CharacterReadDTO
from src.shared.schemas.onboarding import ButtonDTO, OnboardingDraftDTO, OnboardingUIPayloadDTO


class OnboardingService:
    """
    Сервис для управления процессом создания персонажа (Onboarding).
    Работает как Wizard (State Machine).
    Возвращает готовые UI Payload (Текст + Кнопки).
    """

    def __init__(self, session: AsyncSession, session_service: AccountSessionService):
        self.repo = CharactersRepoORM(session)
        self.session_service = session_service

    async def initialize(self, character: CharacterReadDTO) -> OnboardingUIPayloadDTO:
        """
        Инициализирует контекст нового персонажа и возвращает первый шаг (NAME).
        """
        # 1. Создаем сессию через AccountSessionService
        await self.session_service.create_session(character, CoreDomain.ONBOARDING)

        # 2. Возвращаем первый шаг (NAME)
        return self._get_name_payload()

    async def resume_session(self, char_id: int) -> OnboardingUIPayloadDTO:
        """
        Восстанавливает сессию онбординга.
        Определяет текущий шаг на основе заполненных данных.
        """
        context = await self.session_service.get_session(char_id)
        if not context:
            raise SessionExpiredException()

        name = context.bio.get("name")
        gender = context.bio.get("gender")

        # Логика определения шага
        # Если имя дефолтное ("Новый персонаж" или None) -> NAME
        # Если имя есть, но пол дефолтный ("other") -> GENDER
        # Если все есть -> CONFIRM

        # Предполагаем, что "Новый персонаж" и "other" - это дефолты из БД.
        # Но лучше проверять на None или пустую строку, если мы их очищаем.
        # В CharacterReadDTO дефолты могут быть.

        # Упрощенная логика:
        # Если мы на шаге NAME, то имя еще не введено (или дефолтное).
        # Но как отличить "ввел имя" от "еще не ввел"?
        # Мы можем хранить step в ac: (но мы храним только state=ONBOARDING).

        # Давай смотреть по факту:
        if not name or name == "Новый персонаж":
            return self._get_name_payload()

        if not gender or gender == "other":
            return self._get_gender_payload(name)

        return self._get_confirm_payload(name, gender)

    async def set_name(self, char_id: int, name: str) -> OnboardingUIPayloadDTO:
        """
        Устанавливает имя и переходит к выбору пола.
        """
        # 1. Получаем текущую сессию
        context = await self.session_service.get_session(char_id)
        if not context:
            raise SessionExpiredException()

        # 2. Обновляем имя
        context.bio["name"] = name
        await self.session_service.update_bio(char_id, context.bio)

        # 3. Возвращаем следующий шаг (GENDER)
        return self._get_gender_payload(name)

    async def set_gender(self, char_id: int, gender: str) -> OnboardingUIPayloadDTO:
        """
        Устанавливает пол и переходит к подтверждению.
        """
        context = await self.session_service.get_session(char_id)
        if not context:
            raise SessionExpiredException()

        context.bio["gender"] = gender
        await self.session_service.update_bio(char_id, context.bio)

        name = context.bio["name"] or "Hero"
        return self._get_confirm_payload(name, gender)

    async def finalize(self, char_id: int) -> None:
        """
        Завершает создание.
        """
        # TODO:
        # 1. Обновить state в Redis -> SCENARIO
        # 2. Вызвать SystemDispatcher / ScenarioService для старта интро
        # 3. Запустить ARQ Worker для сохранения в БД
        pass

    # --- Private View Generators (Static) ---

    @staticmethod
    def _get_name_payload() -> OnboardingUIPayloadDTO:
        return OnboardingUIPayloadDTO(
            step=OnboardingStepEnum.NAME,
            title="Создание персонажа",
            description=OnboardingResources.get_name_text(),
            buttons=[],
            draft=OnboardingDraftDTO(),
        )

    @staticmethod
    def _get_gender_payload(name: str) -> OnboardingUIPayloadDTO:
        buttons_config = OnboardingResources.get_gender_buttons()
        buttons = [ButtonDTO(**btn) for btn in buttons_config]

        return OnboardingUIPayloadDTO(
            step=OnboardingStepEnum.GENDER,
            title="Выбор пола",
            description=OnboardingResources.get_gender_text(name),
            buttons=buttons,
            draft=OnboardingDraftDTO(name=name),
        )

    @staticmethod
    def _get_confirm_payload(name: str, gender: str) -> OnboardingUIPayloadDTO:
        buttons_config = OnboardingResources.get_confirm_buttons()
        buttons = [ButtonDTO(**btn) for btn in buttons_config]

        return OnboardingUIPayloadDTO(
            step=OnboardingStepEnum.CONFIRM,
            title="Подтверждение",
            description=OnboardingResources.get_confirm_text(name, gender),
            buttons=buttons,
            draft=OnboardingDraftDTO(name=name, gender=gender),
        )
