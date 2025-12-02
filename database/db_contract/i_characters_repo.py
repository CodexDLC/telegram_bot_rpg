from abc import ABC, abstractmethod

from app.resources.schemas_dto.character_dto import (
    CharacterOnboardingUpdateDTO,
    CharacterReadDTO,
    CharacterShellCreateDTO,
    CharacterStatsReadDTO,
    CharacterStatsUpdateDTO,
)


class ICharactersRepo(ABC):
    """
    Абстрактный базовый класс (интерфейс) для репозитория персонажей.

    Определяет контракт для управления основными данными персонажей,
    включая создание, обновление, получение и удаление.
    """

    @abstractmethod
    async def create_character_shell(self, character_data: CharacterShellCreateDTO) -> int:
        """
        Создает "оболочку" персонажа, содержащую только ID пользователя.

        Этот метод используется на первом шаге создания персонажа, когда
        основные данные (имя, пол) еще не известны.

        Args:
            character_data: DTO с `user_id` для создания оболочки.

        Returns:
            Уникальный ID (`character_id`) созданной записи.
        """
        pass

    @abstractmethod
    async def update_character_onboarding(
        self, character_id: int, character_data: CharacterOnboardingUpdateDTO
    ) -> None:
        """
        Обновляет данные персонажа после этапа онбординга.

        Заполняет имя, пол и устанавливает начальную игровую стадию
        для ранее созданной "оболочки".

        Args:
            character_id: Идентификатор персонажа для обновления.
            character_data: DTO с данными (name, gender, game_stage).
        """
        pass

    @abstractmethod
    async def get_character(self, character_id: int) -> CharacterReadDTO | None:
        """
        Находит и возвращает одного персонажа по его `character_id`.

        Args:
            character_id: Уникальный идентификатор персонажа.

        Returns:
            DTO `CharacterReadDTO` с данными персонажа, если он найден,
            иначе - None.
        """
        pass

    @abstractmethod
    async def get_characters(self, user_id: int) -> list[CharacterReadDTO]:
        """
        Возвращает список всех персонажей, принадлежащих одному пользователю.

        Args:
            user_id: Идентификатор пользователя, чьих персонажей нужно найти.

        Returns:
            Список DTO `CharacterReadDTO` персонажей.
            Если персонажей нет, возвращает пустой список.
        """
        pass

    @abstractmethod
    async def delete_characters(self, character_id: int) -> None:
        """
        Удаляет персонажа и все связанные с ним данные.

        Args:
            character_id: Идентификатор персонажа для удаления.
        """
        pass

    @abstractmethod
    async def update_character_game_stage(self, character_id: int, character_game_stage: str) -> None:
        """
        Обновляет поле `game_stage` у конкретного персонажа.

        Args:
            character_id: Идентификатор персонажа для обновления.
            character_game_stage: Новое значение игровой стадии.
        """
        pass


class ICharacterStatsRepo(ABC):
    """
    Абстрактный базовый класс (интерфейс) для репозитория характеристик персонажа.

    Определяет контракт для получения, обновления и модификации
    характеристик персонажа.
    """

    @abstractmethod
    async def get_stats(self, character_id: int) -> CharacterStatsReadDTO | None:
        """
        Возвращает характеристики (статы) персонажа.

        Args:
            character_id: Идентификатор персонажа, чьи характеристики нужны.

        Returns:
            DTO `CharacterStatsReadDTO` с характеристиками, если они найдены,
            иначе - None.
        """
        pass

    @abstractmethod
    async def update_stats(self, character_id: int, stats_data: CharacterStatsUpdateDTO) -> None:
        """
        Полностью перезаписывает все характеристики персонажа.

        Args:
            character_id: Идентификатор персонажа для обновления.
            stats_data: DTO с полным набором новых характеристик.
        """
        pass

    @abstractmethod
    async def add_stats(self, character_id: int, stats_to_add: dict[str, int]) -> CharacterStatsReadDTO | None:
        """
        Атомарно добавляет значения к существующим характеристикам.

        Реализация должна инкрементально обновлять только переданные
        характеристики и возвращать их новое полное состояние.

        Args:
            character_id: Идентификатор персонажа.
            stats_to_add: Словарь, где ключ - название характеристики,
                          а значение - число для добавления (может быть отрицательным).

        Returns:
            DTO `CharacterStatsReadDTO` с обновленными характеристиками
            персонажа или None, если персонаж не найден.
        """
        pass
