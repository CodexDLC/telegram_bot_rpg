from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from common.schemas.response import CoreResponseDTO

if TYPE_CHECKING:
    from game_client.telegram_bot.common.ui.director import GameDirector


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

    async def check_and_switch_state(self, response: CoreResponseDTO, fallback_payload: Any = None) -> Any | None:
        """
        Проверяет, нужно ли сменить стейт на основе ответа от Core.

        Args:
            response: Ответ от Core.
            fallback_payload: Данные, которые будут переданы в новый стейт,
                              если response.payload пустой (None).

        Returns:
            Any: Результат переключения сцены (ViewDTO), если стейт изменился.
            None: Если стейт соответствует ожидаемому (или expected_state не задан).
        """
        if self.expected_state and response.header.current_state != self.expected_state:
            payload_to_send = response.payload
            if payload_to_send is None:
                payload_to_send = fallback_payload

            return await self.director.set_scene(target_state=response.header.current_state, payload=payload_to_send)
        return None
