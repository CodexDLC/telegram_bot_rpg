# tests/integration/test_arena_simulation.py
import json

import pytest
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.core_service.manager.arena_manager import arena_manager
from app.services.core_service.manager.combat_manager import combat_manager

# Импортируем "боевые" части приложения
from app.services.game_service.arena.arena_service import ArenaService
from app.services.game_service.combat.combat_service import CombatService
from database.model_orm import Character

# Настройка отдельного логгера
logger.add("logs/test_battle_report.log", level="INFO", rotation="1 MB", format="{message}")


@pytest.mark.asyncio
async def test_full_arena_cycle(get_async_session):
    session: AsyncSession
    async with get_async_session() as session:
        # 1. SETUP
        char_a_id = await _create_test_char(session, 77701, "Gladiator_A")
        char_b_id = await _create_test_char(session, 77702, "Gladiator_B")

        logger.info(f"🏁 СТАРТ ТЕСТА. Бойцы: {char_a_id} vs {char_b_id}")

        # Clean up
        await arena_manager.remove_from_queue("1v1", char_a_id)
        await arena_manager.remove_from_queue("1v1", char_b_id)
        await combat_manager.delete_player_status(char_a_id)
        await combat_manager.delete_player_status(char_b_id)

        # 2. MATCHMAKING
        service_a = ArenaService(session, char_id=char_a_id)
        service_b = ArenaService(session, char_id=char_b_id)

        await service_a.join_queue("1v1")
        await service_b.join_queue("1v1")

        session_id = await service_a.check_match("1v1", attempt=1)
        if not session_id:
            session_id = await service_b.check_match("1v1", attempt=5)

        assert session_id is not None, "❌ Матч не найден."
        logger.info(f"🎉 БОЙ НАЧАЛСЯ! Session: {session_id}")

        # 3. COMBAT LOOP
        combat = CombatService(session_id)
        round_counter = 0

        logger.info("\n⚔️ --- ХРОНИКА БОЯ --- ⚔️")

        while True:
            round_counter += 1

            # --- ХОД (Exchange) ---
            # Делаем ходы вслепую
            await combat.register_move(char_a_id, char_b_id, None, None)
            await combat.register_move(char_b_id, char_a_id, None, None)

            # --- ЛОГИ (Reading Log) ---
            logs = await combat_manager.get_combat_log_list(session_id)
            if logs:
                # Берем последнюю запись (это текущий раунд)
                last_entry = json.loads(logs[-1])

                logger.info(f"\n🔻 Раунд {round_counter}")
                for line in last_entry.get("logs", []):
                    clean_line = line.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
                    logger.info(f"   {clean_line}")

            # --- 🔥 ОБНОВЛЕНИЕ СОСТОЯНИЯ (State Refresh) ---
            # Важно: Получаем данные ПОСЛЕ удара, чтобы видеть актуальные HP
            actor_a = await combat._get_actor(char_a_id)
            actor_b = await combat._get_actor(char_b_id)

            hp_a = actor_a.state.hp_current
            hp_b = actor_b.state.hp_current

            # Печатаем честный статус-бар
            logger.info(f"   📊 Итог: [A: {hp_a} HP] vs [B: {hp_b} HP]")

            # --- ПРОВЕРКА СМЕРТИ (Death Check) ---
            if hp_a <= 0 or hp_b <= 0:
                logger.info("\n💀 Смертельный исход.")

                if hp_a <= 0 and hp_b <= 0:
                    winner = "🤝 НИЧЬЯ (Double KO)"
                else:
                    winner = "Gladiator_A" if hp_a > 0 else "Gladiator_B"

                logger.info(f"🏆 Результат: {winner}")
                break

            if round_counter > 50:
                logger.error("❌ Лимит раундов.")
                break

        # 4. FINAL CHECK
        meta = await combat_manager.get_session_meta(session_id)
        assert int(meta.get("active")) == 0
        logger.info("\n✅ Тест завершен корректно.")


async def _create_test_char(session: AsyncSession, uid: int, name: str) -> int:
    """Создает тестового чара (без изменений)."""
    from app.resources.schemas_dto.user_dto import UserUpsertDTO
    from database.repositories.ORM.users_repo_orm import UsersRepoORM

    u_repo = UsersRepoORM(session)
    await u_repo.upsert_user(
        UserUpsertDTO(
            telegram_id=uid, first_name=name, username=name, last_name=None, language_code="ru", is_premium=False
        )
    )

    res = await session.execute(select(Character).where(Character.user_id == uid))
    char = res.scalars().first()

    if not char:
        from app.resources.schemas_dto.character_dto import CharacterOnboardingUpdateDTO, CharacterShellCreateDTO
        from database.repositories.ORM.characters_repo_orm import CharactersRepoORM

        c_repo = CharactersRepoORM(session)
        char_id = await c_repo.create_character_shell(CharacterShellCreateDTO(user_id=uid))

        await c_repo.update_character_onboarding(
            char_id, CharacterOnboardingUpdateDTO(name=name, gender="male", game_stage="in_game")
        )

        # Stats
        from app.services.game_service.skill.skill_service import CharacterSkillsService
        from database.repositories import get_character_stats_repo, get_skill_progress_repo, get_skill_rate_repo

        skill_service = CharacterSkillsService(
            get_character_stats_repo(session), get_skill_rate_repo(session), get_skill_progress_repo(session)
        )
        await skill_service.finalize_tutorial_stats(
            char_id,
            {
                "strength": 5,
                "agility": 5,
                "endurance": 15,  # Жирнее
                "intelligence": 1,
                "wisdom": 1,
                "men": 1,
                "perception": 1,
                "charisma": 1,
                "luck": 1,
            },
        )
        return char_id

    return char.character_id
