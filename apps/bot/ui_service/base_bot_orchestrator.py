from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.bot.ui_service.game_director.director import GameDirector


class BaseBotOrchestrator(ABC):
    """
    Базовый класс оркестратора.
    Обязывает реализовать метод render.
    """

    def __init__(self, expected_state: str | None):
        self.expected_state = expected_state
        self._director: GameDirector | None = None

    def set_director(self, director: "GameDirector"):
        self._director = director

    @property
    def director(self) -> "GameDirector":
        if not self._director:
            raise RuntimeError(f"Director not set for {self.__class__.__name__}")
        return self._director

    @abstractmethod
    async def render(self, payload: Any) -> Any:
        """
        Превращает бизнес-данные (payload) в ViewDTO.
        """
        pass
