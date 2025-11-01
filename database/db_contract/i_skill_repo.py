# database/db_contract/i_skill_repo.py
from abc import abstractmethod, ABC
from typing import Optional, List, Dict
from database.model_orm.skill import SkillProgressState
from app.resources.schemas_dto.skill import SkillRateDTO, SkillProgressDTO


class ISkillRateRepo(ABC):
    """
    Контракт для C.R.U.D. таблицы 'character_skill_rates' (БСО)
    """

    @abstractmethod
    async def upsert_skill_rates(self, rates_data: List[Dict[str, any]]) -> None:
        """
        Атомарно (через UPSERT) обновляет ВСЕ ставки БСО.
        (Использует self.session)
        """
        pass

    @abstractmethod
    async def get_all_skill_rates(self, character_id: int) -> List[SkillRateDTO]:
        """
        Возвращает ВСЕ рассчитанные ставки БСО для персонажа.
        (Использует self.session)
        """
        pass


class ISkillProgressRepo(ABC):
    """
    Контракт для C.R.U.D. таблицы 'character_skill_progress'
    """

    @abstractmethod
    async def initialize_all_base_skills(self, character_id: int) -> None:
        """
        (ТВОЙ НОВЫЙ МЕТОД)
        Создает (INSERT) все БАЗОВЫЕ навыки (Уровень 1) для
        персонажа со значением total_xp = 0.
        (Использует self.session)
        """
        pass

    @abstractmethod
    async def add_skill_xp(self, character_id: int, skill_key: str, xp_to_add: int) -> Optional[SkillProgressDTO]:
        """
        Атомарно ДОБАВЛЯЕТ опыт к 'total_xp'.
        (Использует self.session)
        """
        pass

    @abstractmethod
    async def update_skill_state(self, character_id: int, skill_key: str, state: SkillProgressState) -> None:
        """
        Обновляет ТОЛЬКО состояние (PLUS/PAUSE/MINUS).
        (Использует self.session)
        """
        pass

    @abstractmethod
    async def get_all_skills_progress(self, character_id: int) -> List[SkillProgressDTO]:
        """
        Возвращает прогресс ВСЕХ навыков персонажа (включая "нулевые").
        (Использует self.session)
        """
        pass