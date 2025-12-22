# tests/integration/test_arena_simulation.py
import asyncio
import json

import pytest
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories.ORM.characters_repo_orm import CharactersRepoORM
from apps.common.database.repositories.ORM.users_repo_orm import UsersRepoORM
from apps.common.schemas_dto import (
    CharacterOnboardingUpdateDTO,
    CharacterShellCreateDTO,
    CombatSessionContainerDTO,
    UserUpsertDTO,
)
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.arena_manager import ArenaManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.game_core.game_service.arena.service_1v1 import Arena1v1Service
from apps.game_core.game_service.combat.combat_orchestrator_rbc import CombatOrchestratorRBC
from apps.game_core.game_service.combat.session.combat_lifecycle_service import CombatLifecycleService


async def _create_test_char(session: AsyncSession, user_id: int, name: str) -> int:
    user_repo = UsersRepoORM(session)
    await user_repo.upsert_user(
        UserUpsertDTO(
            telegram_id=user_id,
            first_name=name,
            last_name="Test",
            username=name.lower(),
            language_code="ru",
            is_premium=False,
        )
    )

    char_repo = CharactersRepoORM(session)
    char_id = await char_repo.create_character_shell(CharacterShellCreateDTO(user_id=user_id))
    await char_repo.update_character_onboarding(
        char_id, CharacterOnboardingUpdateDTO(name=name, gender="male", game_stage="in_game")
    )

    return char_id


@pytest.mark.asyncio
async def test_full_arena_cycle(get_async_session, app_container):
    session: AsyncSession
    async with get_async_session() as session:
        # 1. SETUP
        char_a_id = await _create_test_char(session, 77701, "Gladiator_A")
        char_b_id = await _create_test_char(session, 77702, "Gladiator_B")

        logger.info(f"🏁 СТАРТ ТЕСТА. Бойцы: {char_a_id} vs {char_b_id}")

        arena_manager: ArenaManager = app_container.arena_manager
        combat_manager: CombatManager = app_container.combat_manager
        account_manager: AccountManager = app_container.account_manager

        # Clean up
        await arena_manager.remove_from_queue("1v1", char_a_id)
        await arena_manager.remove_from_queue("1v1", char_b_id)
        await combat_manager.delete_player_status(char_a_id)
        await combat_manager.delete_player_status(char_b_id)

        await session.commit()

        # 2. MATCHMAKING
        service_a = Arena1v1Service(session, char_a_id, arena_manager, combat_manager, account_manager)
        service_b = Arena1v1Service(session, char_b_id, arena_manager, combat_manager, account_manager)

        await service_a.join_queue()
        await service_b.join_queue()

        session_id = None
        for attempt in range(1, 11):
            session_id = await service_a.check_and_match(attempt=attempt)
            if session_id:
                break
            session_id = await service_b.check_and_match(attempt=attempt)
            if session_id:
                break
            await asyncio.sleep(0.1)

        assert session_id is not None, "❌ Матч не найден после нескольких попыток."
        logger.info(f"🎉 БОЙ НАЧАЛСЯ! Session: {session_id}")

        # 3. COMBAT LOOP
        orchestrator = CombatOrchestratorRBC(session, combat_manager, account_manager)
        round_counter = 0

        logger.info("\n⚔️ --- ХРОНИКА БОЯ --- ⚔️")

        while True:
            round_counter += 1

            await orchestrator.register_move(session_id, char_a_id, char_b_id, {})
            await orchestrator.register_move(session_id, char_b_id, char_a_id, {})

            logs = await combat_manager.get_combat_log_list(session_id)
            if logs:
                last_entry = json.loads(logs[-1])
                logger.info(f"\n🔻 Раунд {round_counter}")
                for line in last_entry.get("logs", []):
                    clean_line = str(line).replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
                    logger.info(f"    {clean_line}")

            actor_a_json = await combat_manager.get_rbc_actor_state_json(session_id, char_a_id)
            actor_b_json = await combat_manager.get_rbc_actor_state_json(session_id, char_b_id)
            actor_a = CombatSessionContainerDTO.model_validate_json(actor_a_json) if actor_a_json else None
            actor_b = CombatSessionContainerDTO.model_validate_json(actor_b_json) if actor_b_json else None

            assert actor_a is not None and actor_a.state is not None
            assert actor_b is not None and actor_b.state is not None

            hp_a = actor_a.state.hp_current
            hp_b = actor_b.state.hp_current

            logger.info(f"    📊 Итог: [A: {hp_a} HP] vs [B: {hp_b} HP]")

            if hp_a <= 0 or hp_b <= 0:
                logger.info("\n💀 Смертельный исход.")
                winner = "Gladiator_A" if hp_a > 0 else "Gladiator_B"
                if hp_a <= 0 and hp_b <= 0:
                    winner = "🤝 НИЧЬЯ (Double KO)"
                logger.info(f"🏆 Результат: {winner}")
                break

            if round_counter > 50:
                logger.error("❌ Лимит раундов.")
                lifecycle_service = CombatLifecycleService(combat_manager, account_manager)
                await lifecycle_service.finish_battle(session_id, "draw_by_limit")
                break

        # 4. FINAL CHECK
        # ИСПРАВЛЕНО: Используем get_rbc_session_meta
        meta = await combat_manager.get_rbc_session_meta(session_id)
        assert meta is not None
        assert meta.get("active") == "0"
        logger.info("✅ Тест арены успешно завершен.")
