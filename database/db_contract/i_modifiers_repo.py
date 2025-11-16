# database/db_contract/i_modifiers_repo.py
from abc import abstractmethod, ABC
from typing import Optional, Dict, Any

from app.resources.schemas_dto.modifer_dto import CharacterModifiersDTO, CharacterModifiersSaveDto

class ICharacterModifiersRepo(ABC):

    @abstractmethod
    async def get_modifiers(self, character_id: int) -> Optional[CharacterModifiersDTO]:
        """
        Получает ВСЕ модификаторы (DTO для чтения) для одного персонажа.
        """
        pass

    @abstractmethod
    async def save_modifiers(self, character_id: int, data: CharacterModifiersSaveDto) -> None:
        """
        Полностью перезаписывает (UPDATE) все модификаторы персонажа,
        используя DTO для сохранения.
        """
        pass

    @abstractmethod
    async def update_specific_modifiers(self, character_id: int, updates: Dict[str, Any]) -> None:
        """
        Частично обновляет (UPDATE) только указанные поля в модификаторах.
        Пример: updates = {"armor_head": "2d6", "hp_max": 150}
        """
        pass