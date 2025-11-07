# database/db_contract/i_skill_repo.py
from abc import abstractmethod, ABC
from typing import Optional, List, Dict
from database.model_orm.skill import SkillProgressState
from app.resources.schemas_dto.skill import SkillRateDTO, SkillProgressDTO


class ISkillRateRepo(ABC):
    """
    Абстрактный базовый класс (интерфейс) для репозитория ставок навыков (БСО).

    Определяет контракт для работы с таблицей `character_skill_rates`.
    Эта таблица хранит рассчитанные "ставки" или коэффициенты для каждого навыка,
    которые влияют на его развитие.
    """

    @abstractmethod
    async def upsert_skill_rates(self, rates_data: List[Dict[str, any]]) -> None:
        """
        Массово создает или обновляет ставки навыков для персонажа.

        Реализация должна использовать атомарную операцию "UPSERT"
        (например, INSERT ... ON CONFLICT ... DO UPDATE), чтобы обновить
        существующие записи или создать новые за один вызов.

        Args:
            rates_data (List[Dict[str, any]]): Список словарей, где каждый
                словарь представляет одну запись ставки навыка и содержит
                `character_id`, `skill_key` и другие поля.

        Returns:
            None
        """
        pass

    @abstractmethod
    async def get_all_skill_rates(self, character_id: int) -> List[SkillRateDTO]:
        """
        Возвращает все рассчитанные ставки навыков для одного персонажа.

        Args:
            character_id (int): ID персонажа.

        Returns:
            List[SkillRateDTO]: Список DTO со ставками навыков. Если ставок нет,
                                возвращает пустой список.
        """
        pass


class ISkillProgressRepo(ABC):
    """
    Абстрактный базовый класс (интерфейс) для репозитория прогресса навыков.

    Определяет контракт для работы с таблицей `character_skill_progress`,
    которая отслеживает опыт и состояние каждого навыка у персонажа.
    """

    @abstractmethod
    async def initialize_all_base_skills(self, character_id: int) -> None:
        """
        Инициализирует записи для всех базовых навыков для нового персонажа.

        Для каждого базового навыка (например, из предопределенного списка)
        создает запись в таблице с начальным уровнем (1) и нулевым опытом (0).

        Args:
            character_id (int): ID персонажа, для которого инициализируются навыки.

        Returns:
            None
        """
        pass

    @abstractmethod
    async def add_skill_xp(self, character_id: int, skill_key: str, xp_to_add: int) -> Optional[SkillProgressDTO]:
        """
        Атомарно добавляет опыт к указанному навыку персонажа.

        Args:
            character_id (int): ID персонажа.
            skill_key (str): Ключ навыка (например, 'strength_athletics').
            xp_to_add (int): Количество опыта для добавления.

        Returns:
            Optional[SkillProgressDTO]: Обновленный DTO прогресса навыка,
                                        если запись найдена и обновлена.
                                        Иначе - None.
        """
        pass

    @abstractmethod
    async def update_skill_state(self, character_id: int, skill_key: str, state: SkillProgressState) -> None:
        """
        Обновляет состояние развития навыка (PLUS, PAUSE, MINUS).

        Это позволяет игроку управлять тем, какие навыки будут приоритетно
        получать опыт.

        Args:
            character_id (int): ID персонажа.
            skill_key (str): Ключ навыка.
            state (SkillProgressState): Новое состояние (Enum).

        Returns:
            None
        """
        pass

    @abstractmethod
    async def get_all_skills_progress(self, character_id: int) -> List[SkillProgressDTO]:
        """
        Возвращает прогресс всех навыков для одного персонажа.

        Включает в себя все навыки, даже те, у которых нет опыта.

        Args:
            character_id (int): ID персонажа.

        Returns:
            List[SkillProgressDTO]: Список DTO с прогрессом всех навыков.
                                    Если записи отсутствуют, возвращает
                                    пустой список.
        """
        pass
