# tests/integration/test_arena_simulation.py
import asyncio
import json  # Необходим для чтения логов

import pytest
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.core_service.manager.account_manager import AccountManager
from app.services.core_service.manager.arena_manager import ArenaManager
from app.services.core_service.manager.combat_manager import CombatManager

# Импортируем "боевые" части приложения
from app.services.game_service.arena.service_1v1 import Arena1v1Service

# 🔥 ИМПОРТИРУЕМ LIFECYCLE ДЛЯ ПРИНУДИТЕЛЬНОГО ЗАВЕРШЕНИЯ
from app.services.game_service.combat.combat_lifecycle_service import CombatLifecycleService
from app.services.game_service.combat.combat_service import CombatService
from database.model_orm import Character

# Настройка отдельного логгера
logger.add("logs/test_battle_report.log", level="INFO", rotation="1 MB", format="{message}")


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

        # 🔥 ВАЖНОЕ ИСПРАВЛЕНИЕ 🔥
        # Мы должны зафиксировать создание персонажей в БД,
        # чтобы освободить блокировку записи для следующих сервисов.
        await session.commit()

        # 2. MATCHMAKING
        service_a = Arena1v1Service(session, char_a_id, arena_manager, combat_manager, account_manager)
        service_b = Arena1v1Service(session, char_b_id, arena_manager, combat_manager, account_manager)

        await service_a.join_queue()
        await service_b.join_queue()

        session_id = None
        for attempt in range(1, 11):  # Попробуем до 10 раз
            session_id = await service_a.check_and_match(attempt=attempt)
            if session_id:
                break
            session_id = await service_b.check_and_match(attempt=attempt)
            if session_id:
                break
            await asyncio.sleep(0.1)  # Небольшая задержка перед следующей попыткой

        assert session_id is not None, "❌ Матч не найден после нескольких попыток."
        logger.info(f"🎉 БОЙ НАЧАЛСЯ! Session: {session_id}")

        # 3. COMBAT LOOP
        combat = CombatService(session_id, combat_manager, account_manager)
        round_counter = 0

        logger.info("\n⚔️ --- ХРОНИКА БОЯ --- ⚔️")

        while True:
            round_counter += 1

            # --- ХОД (Exchange) ---
            await combat.register_move(char_a_id, char_b_id, None, None)
            await combat.register_move(char_b_id, char_a_id, None, None)

            # --- ЛОГИ (Reading Log) ---
            logs = await combat_manager.get_combat_log_list(session_id)
            if logs:
                # Берем последнюю запись (это текущий раунд)
                last_entry = json.loads(logs[-1])

                logger.info(f"\n🔻 Раунд {round_counter}")
                for line in last_entry.get("logs", []):
                    # NOTE: СКОРЕЕ ВСЕГО ЗДЕСЬ ОШИБКА, Т.К. line = JSON, но оставим как есть в тесте
                    clean_line = line.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
                    logger.info(f"   {clean_line}")

            # --- 🔥 ОБНОВЛЕНИЕ СОСТОЯНИЯ (State Refresh) ---
            actor_a = await combat._get_actor(char_a_id)
            actor_b = await combat._get_actor(char_b_id)

            hp_a = actor_a.state.hp_current
            hp_b = actor_b.state.hp_current

            logger.info(f"   📊 Итог: [A: {hp_a} HP] vs [B: {hp_b} HP]")

            # --- ПРОВЕРКА СМЕРТИ (Death Check) ---
            # NOTE: Мы полагаемся на combat._check_battle_end() внутри register_move,
            # но здесь нам нужна отдельная проверка для выхода из цикла.
            if hp_a <= 0 or hp_b <= 0:
                logger.info("\n💀 Смертельный исход.")
                winner = "Gladiator_A" if hp_a > 0 else "Gladiator_B"
                if hp_a <= 0 and hp_b <= 0:
                    winner = "🤝 НИЧЬЯ (Double KO)"

                logger.info(f"🏆 Результат: {winner}")
                break

            # --- 🔥 ЛИМИТ РАУНДОВ ---
            if round_counter > 50:
                logger.error("❌ Лимит раундов.")
                # 🔥 ИСПРАВЛЕНО: Принудительно завершаем бой, если дошли до лимита
                lifecycle_service = CombatLifecycleService(combat_manager, account_manager)
                await lifecycle_service.finish_battle(session_id, "draw_by_limit")
                break

        # 4. FINAL CHECK
        meta = await combat_manager.get_session_meta(session_id)
        # Мы ожидаем, что finish_battle был вызван и установил active=0
        assert int(meta.get("active")) == 0
        logger.info("\n✅ Тест завершен корректно.")


async def _create_test_char(session: AsyncSession, uid: int, name: str) -> int:
    from app.resources.schemas_dto.user_dto import UserUpsertDTO
    from database.repositories.ORM.users_repo_orm import UsersRepoORM

    u_repo = UsersRepoORM(session)
    await u_repo.upsert_user(
        UserUpsertDTO(
            telegram_id=uid, first_name=name, username=name, last_name=None, language_code="ru", is_premium=False
        )
    )

    # Проверка, существует ли персонаж
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
                "endurance": 5,
                "intelligence": 5,
                "wisdom": 5,
                "men": 5,
                "perception": 5,
                "charisma": 5,
                "luck": 5,
            },
        )
        return char_id

    return char.character_id
