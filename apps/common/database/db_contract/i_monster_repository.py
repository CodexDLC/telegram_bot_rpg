from abc import ABC, abstractmethod
from uuid import UUID

from apps.common.database.model_orm.monster import GeneratedClanORM, GeneratedMonsterORM


class IMonsterRepository(ABC):
    """
    Интерфейс репозитория монстров.
    Разделяет логику генерации (Unique Hash) и логику спавна в бою (Context Hash).
    """

    # --- МЕТОДЫ ДЛЯ ФАБРИКИ (GENERATION FLOW) ---

    @abstractmethod
    async def get_clan_by_unique_hash(self, unique_hash: str) -> GeneratedClanORM | None:
        """
        Ищет конкретный клан по уникальному ключу (Family + Tier + Biome + Anchor).
        Используется Фабрикой, чтобы проверить, генерировали ли мы уже "Орков в Лесу Т2".
        """
        pass

    @abstractmethod
    async def create_clan_with_members(
        self, clan_orm: GeneratedClanORM, monsters_orm: list[GeneratedMonsterORM]
    ) -> GeneratedClanORM:
        """
        Сохраняет новый клан и всех его монстров в одной транзакции.
        """
        pass

    # --- МЕТОДЫ ДЛЯ БОЯ (COMBAT FLOW) ---

    @abstractmethod
    async def get_all_clans_by_context(self, context_hash: str) -> list[GeneratedClanORM]:
        """
        Ищет ВСЕ кланы, доступные в данном контексте (Tier + Biome + Anchor).
        Используется Спавнером, чтобы получить список кандидатов (Орки, Волки, Бандиты)
        и выбрать случайного врага для игрока.
        """
        pass

    @abstractmethod
    async def get_monster_by_id(self, monster_id: UUID | str) -> GeneratedMonsterORM | None:
        """
        Загружает конкретного монстра (со статами) для инициализации боевой сессии.
        Должен подгружать данные клана (relationship).
        """
        pass

    # --- МЕТОДЫ ДЛЯ АДМИНКИ И ДРУГИХ СИСТЕМ ---

    @abstractmethod
    async def get_all_clans(self) -> list[GeneratedClanORM]:
        """
        Загружает ВСЕ существующие кланы с их участниками.
        Используется для админ-панелей и глобальных отчетов.
        """
        pass

    @abstractmethod
    async def get_clans_by_zone(self, zone_id: str) -> list[GeneratedClanORM]:
        """
        Загружает все кланы в указанной зоне.
        """
        pass

    # --- ВСПОМОГАТЕЛЬНЫЕ ---

    @abstractmethod
    async def get_monsters_by_role_and_threat(
        self, role: str, min_threat: int, max_threat: int, limit: int = 5
    ) -> list[GeneratedMonsterORM]:
        """
        (Опционально) Поиск случайных врагов по критериям силы,
        если спавн идет не через клановую систему, а через случайные энкаунтеры.
        """
        pass
