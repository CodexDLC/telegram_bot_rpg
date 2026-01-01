# apps/game_core/modules/combat/session/initialization/combat_lifecycle_service.py
import json
import random
import time
from collections import defaultdict
from typing import Any, NamedTuple

from loguru import logger as log
from redis.asyncio.client import Pipeline

from apps.common.services.core_service import CombatManager
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.context_manager import ContextRedisManager
from apps.common.services.core_service.redis_key import RedisKeys as Rk


class SessionDataDTO(NamedTuple):
    """DTO for transferring assembled data to the persistence method."""

    meta: dict[str, Any]
    actors: dict[str, dict[str, Any]]  # final_id -> {field: value} (HASH fields)
    queues: dict[str, list[str]]  # final_id -> [enemy_id, ...]


class CombatLifecycleService:
    """
    Service for managing the lifecycle of combat sessions.
    Responsible for creation (assembling from templates) and finalization (cleanup) of the session.
    """

    def __init__(
        self,
        combat_manager: CombatManager,
        account_manager: AccountManager,
        context_manager: ContextRedisManager,
    ):
        self.combat_manager = combat_manager
        self.account_manager = account_manager
        self.context_manager = context_manager

    # --- Public API ---

    async def create_battle(self, session_id: str, config: dict[str, Any]) -> None:
        """
        Main method for creating a session.
        Orchestrates loading, assembly, and persistence.

        Args:
            session_id: Unique Session UUID.
            config: Configuration containing 'mode' and 'teams_config'.
        """
        mode = config.get("mode", "standard")
        teams_payload = config.get("teams_config", {})
        ttl = config.get("ttl", 3600)

        log.info(f"Lifecycle | create_session id={session_id} mode={mode}")

        # 1. Load Templates (MGET)
        templates_map = await self._load_templates(teams_payload)

        # 2. Assemble Teams and Actors (In-Memory)
        session_data = self._assemble_session_data(session_id, mode, teams_payload, templates_map)

        # 3. Persist to Redis (Pipeline)
        await self._persist_session(session_id, session_data, ttl)

    async def complete_session(self, session_id: str, results: dict) -> None:
        """
        Finalizes the session, cleans up Redis, and unlinks players.
        """
        log.info(f"Lifecycle | complete_session id={session_id} results={results}")

        # 1. Get participant list from Meta (actors_info)
        meta = await self.combat_manager.get_rbc_session_meta(session_id)
        participant_ids = []

        if meta and "actors_info" in meta:
            try:
                actors_info = json.loads(meta["actors_info"])
                participant_ids = list(actors_info.keys())
            except json.JSONDecodeError:
                log.error(f"Lifecycle | Failed to decode actors_info for session {session_id}")

        # 2. Cleanup Redis (queues, bullets, set history TTL)
        await self.combat_manager.cleanup_rbc_session(session_id)

        # 3. Unlink players (release them for new battles)
        if participant_ids:
            await self.account_manager.bulk_unlink_combat_session(
                [int(pid) for pid in participant_ids if pid.isdigit()]
            )

    # --- Private Helpers ---

    async def _load_templates(self, teams_payload: dict) -> dict[str, dict]:
        """
        Collects all 'ref' UUIDs and performs a single MGET request.
        """
        unique_refs = set()
        for members in teams_payload.values():
            for member in members:
                unique_refs.add(member["ref"])

        if not unique_refs:
            log.warning("Lifecycle | No participants in payload")
            return {}

        # MGET via ContextManager
        templates = await self.context_manager.get_context_batch(list(unique_refs))

        # Integrity check
        if len(templates) != len(unique_refs):
            missing = unique_refs - set(templates.keys())
            log.error(f"Lifecycle | Missing templates for refs: {missing}")
            # We raise an error because we cannot build a valid session without source data
            raise ValueError(f"Missing templates for refs: {missing}")

        return templates

    def _assemble_session_data(
        self, session_id: str, mode: str, teams_payload: dict, templates_map: dict
    ) -> SessionDataDTO:
        """
        Core assembly logic: cloning, naming, matchups.
        """
        final_teams = {}  # {"blue": ["id1", "id2"]}
        actors_data = {}  # {"id1": {HASH_FIELDS}}
        all_ids = []  # ["id1", "id2", ...]

        # Mapping dictionary: who is in which team (for queue generation)
        id_to_team = {}

        # 1. Iterate through teams
        for color, members in teams_payload.items():
            team_ids = []
            name_counter: dict[str, int] = defaultdict(int)

            for member in members:
                ref = member["ref"]
                tpl_id = str(member["id"])

                if ref not in templates_map:
                    continue

                # Increment counter for this template
                name_counter[tpl_id] += 1
                count = name_counter[tpl_id]

                # --- ID Generation Logic ---
                if tpl_id.isdigit():
                    # Player
                    final_id = f"-{tpl_id}" if mode == "shadow" and color == "red" else tpl_id
                else:
                    # Monster/AI
                    final_id = tpl_id if tpl_id.startswith("-") and tpl_id[1:].isdigit() else f"{tpl_id}_{count}"

                # --- JSON Patching & Structuring ---
                source_json = templates_map[ref]

                # Используем CombatActorReadDTO для валидации и фильтрации
                from apps.common.schemas_dto.combat_context_read import CombatActorReadDTO

                try:
                    actor_dto = CombatActorReadDTO.model_validate(source_json)
                except Exception as e:  # noqa: BLE001
                    log.error(f"Lifecycle | Invalid template data for {ref}: {e}")
                    continue

                # Name Patching
                original_name = actor_dto.meta.get("name", "Unknown")
                new_name = original_name
                if mode == "shadow" and color == "red":
                    new_name = f"Shadow {original_name}"
                elif count > 1:
                    new_name = f"{original_name} {count}"

                # Determine AI flag
                is_ai = not final_id.isdigit()  # Negative or String -> AI

                # --- Build Actor Hash Fields (RBC v2.0 Schema) ---

                # 1. v:raw (Math Model) - Source of Truth
                math_model = actor_dto.math_model

                # 2. Vitals
                vitals = actor_dto.vitals

                # 3. Loadout
                loadout = actor_dto.loadout

                # Объединяем скиллы и абилки в единый список действий
                skills_list = loadout.get("skills", [])
                abilities_list = loadout.get("abilities", [])
                combined_actions = skills_list + abilities_list

                # 4. Meta (Lightweight for UI/Listing)
                actor_meta = {
                    "name": new_name,
                    "is_ai": is_ai,
                    "team": color,
                    "template_id": tpl_id,
                    "type": actor_dto.meta.get("type", "unknown"),
                }

                actor_fields = {
                    "v:raw": json.dumps(math_model),
                    "v:req_ver": 1,
                    "v:cache_ver": 0,  # Force calculation
                    "s:hp": vitals.get("hp_current", 100),
                    "s:en": vitals.get("energy_current", 100),
                    "s:belt": json.dumps(loadout.get("belt", [])),
                    "s:skills": json.dumps(combined_actions),
                    "meta": json.dumps(actor_meta),
                }

                # Store
                actors_data[final_id] = actor_fields
                team_ids.append(final_id)
                all_ids.append(final_id)
                id_to_team[final_id] = color

            final_teams[color] = team_ids

        # 2. Queue Generation (Matchups)
        queues = {}
        for my_id in all_ids:
            my_team = id_to_team[my_id]
            enemies = []
            for other_id in all_ids:
                if id_to_team[other_id] != my_team:
                    enemies.append(other_id)

            random.shuffle(enemies)
            queues[my_id] = enemies

        # 3. Meta Assembly
        actors_info_map = {}
        for aid in all_ids:
            if aid.isdigit():
                actors_info_map[aid] = "player"
            else:
                actors_info_map[aid] = "ai"

        meta = {
            "mode": mode,
            "teams": json.dumps(final_teams),
            "active": 1,
            "start_time": int(time.time()),
            "actors_info": json.dumps(actors_info_map),
        }

        return SessionDataDTO(meta=meta, actors=actors_data, queues=queues)

    async def _persist_session(self, session_id: str, data: SessionDataDTO, ttl: int) -> None:
        """
        Writes data to Redis via Pipeline using RedisService.
        """

        def _fill_pipe(pipe: Pipeline) -> None:
            # 1. Meta
            pipe.hset(Rk.get_rbc_meta_key(session_id), mapping=data.meta)
            pipe.expire(Rk.get_rbc_meta_key(session_id), ttl)

            # 2. Actors (Each actor gets their own HASH key)
            for aid, fields in data.actors.items():
                key = Rk.get_rbc_actor_key(session_id, str(aid))
                pipe.hset(key, mapping=fields)
                pipe.expire(key, ttl)

            # 3. Queues
            for aid, enemies in data.queues.items():
                if enemies:
                    key = Rk.get_combat_exchanges_key(session_id, str(aid))
                    pipe.rpush(key, *enemies)
                    pipe.expire(key, ttl)

        await self.combat_manager.redis_service.execute_pipeline(_fill_pipe)
