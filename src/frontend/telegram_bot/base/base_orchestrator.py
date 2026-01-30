from typing import TYPE_CHECKING, Any

from src.frontend.telegram_bot.base.view_dto import UnifiedViewDTO
from src.shared.schemas.response import CoreCompositeResponseDTO, CoreResponseDTO

if TYPE_CHECKING:
    from src.frontend.telegram_bot.services.director.director import GameDirector


class BaseBotOrchestrator:
    """
    Базовый класс оркестратора.
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

    async def render_content(self, payload: Any) -> Any:
        """
        Превращает бизнес-данные (payload) в ViewDTO контента.
        Должен быть реализован в наследниках, использующих process_response.
        """
        raise NotImplementedError(f"render_content not implemented in {self.__class__.__name__}")

    async def render(self, payload: Any) -> Any:
        """
        Основной метод рендеринга.
        Может быть переопределен в наследниках.
        По умолчанию пытается обработать ответ через process_response или вызывает render_content.
        """
        if isinstance(payload, (CoreResponseDTO, CoreCompositeResponseDTO)):
            return await self.process_response(payload)
        return await self.render_content(payload)

    async def process_response(self, response: CoreResponseDTO | CoreCompositeResponseDTO) -> UnifiedViewDTO:
        """
        Универсальный метод обработки ответа от Gateway.
        Поддерживает как обычные, так и композитные ответы.
        """
        # 1. Проверка редиректа (смена стейта)
        if self.expected_state and response.header.current_state != self.expected_state:
            # Если стейт изменился, делегируем директору смену сцены
            return await self.director.set_scene(feature=response.header.current_state, payload=response.payload)

        # 2. Рендеринг основного контента
        content_view = None
        if response.payload is not None:
            content_view = await self.render_content(response.payload)

        # 3. Рендеринг меню (только для Composite)
        menu_view = None
        if isinstance(response, CoreCompositeResponseDTO) and response.menu_payload:
            # TODO: Реализовать в Director метод render_menu или вызывать MenuService напрямую
            pass

        return UnifiedViewDTO(content=content_view, menu=menu_view)

    async def check_and_switch_state(self, response: CoreResponseDTO, fallback_payload: Any = None) -> Any | None:
        """
        Legacy метод. Используйте process_response.
        """
        if self.expected_state and response.header.current_state != self.expected_state:
            payload_to_send = response.payload
            if payload_to_send is None:
                payload_to_send = fallback_payload

            return await self.director.set_scene(feature=response.header.current_state, payload=payload_to_send)
        return None
