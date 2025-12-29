from abc import ABC, abstractmethod
from typing import Any

from apps.common.database.model_orm.skill import SkillProgressState
from apps.common.schemas_dto.skill import SkillProgressDTO, SkillRateDTO


class ISkillRateRepo(ABC):
    """
    Абстрактный базовый класс (интерфейс) для репозитория ставок навыков.

    Определяет контракт для работы с таблицей `character_skill_rates`,
    которая хранит рассчитанные "ставки" или коэффициенты для каждого навыка,
    влияющие на его развитие.
    """

    @abstractmethod
    async def upsert_skill_rates(self, rates_data: list[dict[str, Any]]) -> None:
        """
        Массово создает или обновляет ставки опыта для навыков персонажа.

        Реализация должна использовать атомарную операцию "UPSERT"
        (например, INSERT ... ON CONFLICT ... DO UPDATE), чтобы обновить
        существующие записи или создать новые за один вызов.

        Args:
            rates_data: Список словарей, где каждый словарь представляет
                        одну запись ставки навыка и содержит `character_id`,
                        `skill_key` и `xp_per_tick`.
        """
        pass

    @abstractmethod
    async def get_all_skill_rates(self, character_id: int) -> list[SkillRateDTO]:
        """
        Возвращает все рассчитанные ставки опыта для навыков одного персонажа.

        Args:
            character_id: Идентификатор персонажа.

        Returns:
            Список DTO `SkillRateDTO` со ставками навыков.
            Возвращает пустой список, если ставок не найдено.
        """
        pass


class ISkillProgressRepo(ABC):
    """
    Абстрактный базовый класс (интерфейс) для репозитория прогресса навыков.

    Определяет контракт для работы с таблицей `character_skill_progress`,
    которая отслеживает накопленный опыт и текущее состояние каждого навыка
    у персонажа.
    """

    @abstractmethod
    async def initialize_all_base_skills(self, character_id: int) -> None:
        """
        Инициализирует записи для всех базовых навыков для нового персонажа.

        Для каждого базового навыка (например, из предопределенного списка)
        создает запись в таблице с начальным уровнем и нулевым опытом.

        Args:
            character_id: Идентификатор персонажа, для которого инициализируются навыки.
        """
        pass

    @abstractmethod
    async def add_skill_xp(self, character_id: int, skill_key: str, xp_to_add: int) -> SkillProgressDTO | None:
        """
        Атомарно добавляет указанное количество опыта к навыку персонажа.

        Args:
            character_id: Идентификатор персонажа.
            skill_key: Ключ навыка (например, 'melee_combat').
            xp_to_add: Количество опыта для добавления.

        Returns:
            Обновленный DTO `SkillProgressDTO` прогресса навыка,
            если запись найдена и обновлена. Иначе - None.
        """
        pass

    @abstractmethod
    async def update_skill_state(self, character_id: int, skill_key: str, state: SkillProgressState) -> None:
        """
        Обновляет состояние развития навыка (PLUS, PAUSE, MINUS).

        Это позволяет игроку управлять тем, какие навыки будут приоритетно
        получать опыт.

        Args:
            character_id: Идентификатор персонажа.
            skill_key: Ключ навыка.
            state: Новое состояние навыка (Enum `SkillProgressState`).
        """
        pass

    @abstractmethod
    async def update_skill_unlocked_state(self, character_id: int, skill_key_list: list[str], state: bool) -> None:
        """
        Массово обновляет статус `is_unlocked` для списка навыков персонажа.

        Этот метод должен найти все записи, соответствующие `character_id`
        и ключам в `skill_key_list`, и установить их поле `is_unlocked`
        в значение, переданное в `state`.

        Args:
            character_id: Идентификатор персонажа, чьи навыки обновляются.
            skill_key_list: Список строковых ключей навыков, которые нужно обновить.
            state: Новое состояние для `is_unlocked` (True - разблокирован, False - заблокирован).
        """
        pass

    @abstractmethod
    async def get_all_skills_progress(self, character_id: int) -> list[SkillProgressDTO]:
        """
        Возвращает прогресс всех навыков для одного персонажа.

        Включает в себя все навыки, даже те, у которых нет опыта.

        Args:
            character_id: Идентификатор персонажа.

        Returns:
            Список DTO `SkillProgressDTO` с прогрессом всех навыков.
            Возвращает пустой список, если записи отсутствуют.
        """
        pass

    @abstractmethod
    async def get_all_skills_progress_batch(self, character_ids: list[int]) -> dict[int, list[SkillProgressDTO]]:
        """
        Возвращает прогресс навыков для списка персонажей.

        Args:
            character_ids: Список ID персонажей.

        Returns:
            Словарь {character_id: [skills]}.
        """
        pass
