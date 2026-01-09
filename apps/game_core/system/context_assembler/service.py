# apps/game_core/system/context_assembler/service.py
import asyncio
from typing import Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.services.redis.manager.account_manager import AccountManager
from apps.common.services.redis.manager.context_manager import ContextRedisManager
from apps.game_core.system.context_assembler.dtos import ContextRequestDTO, ContextResponseDTO
from apps.game_core.system.context_assembler.logic.monster_assembler import MonsterAssembler
from apps.game_core.system.context_assembler.logic.player_assembler import PlayerAssembler


class ContextAssemblerOrchestrator:
    """
    Главный оркестратор сборки контекста.
    """

    def __init__(
        self,
        session: AsyncSession,
        account_manager: AccountManager,
        context_manager: ContextRedisManager,
    ):
        self.context_manager = context_manager
        self.strategies = {
            "player": PlayerAssembler(session, account_manager, self.context_manager),
            "monster": MonsterAssembler(session, account_manager, self.context_manager),
        }

    async def get_entry_point(self, action: str, context: dict[str, Any]) -> ContextResponseDTO:
        """
        Единая точка входа для соответствия протоколу CoreOrchestratorProtocol.
        """
        if action == "assemble":
            # Превращаем dict context в DTO
            request = ContextRequestDTO(**context)
            return await self.prepare_bulk_context(request)

        log.error(f"ContextAssembler | Unknown action: {action}")
        raise ValueError(f"Unknown action for ContextAssembler: {action}")

    async def prepare_bulk_context(self, request: ContextRequestDTO) -> ContextResponseDTO:
        """
        Главный публичный метод.
        """
        log.info(f"PrepareBulkContext | request: {request.model_dump_json(exclude_defaults=True)}")

        tasks = []
        task_mapping = []

        request_dict = request.model_dump()
        for entity_type, ids_list in request_dict.items():
            if not isinstance(ids_list, list) or not ids_list:
                continue

            clean_entity_type = entity_type.removesuffix("_ids")

            assembler = self.strategies.get(clean_entity_type)
            if assembler:
                tasks.append(assembler.process_batch(ids_list, request.scope))
                task_mapping.append(clean_entity_type)

        if not tasks:
            return ContextResponseDTO()

        results_list = await asyncio.gather(*tasks)

        final_response = ContextResponseDTO()
        for entity_type, result_tuple in zip(task_mapping, results_list, strict=False):
            success_map, error_list = result_tuple

            if hasattr(final_response, entity_type):
                setattr(final_response, entity_type, success_map)

            if error_list:
                final_response.errors[entity_type] = error_list

        log.info(f"PrepareBulkContext | response: {final_response.model_dump_json(exclude_defaults=True)}")
        return final_response
