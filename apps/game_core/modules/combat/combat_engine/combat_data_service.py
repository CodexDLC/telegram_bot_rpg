import json
from typing import Any

# Инфраструктура
from apps.common.services.redis.manager.combat_manager import CombatManager

# DTOs
from apps.game_core.modules.combat.dto.combat_internal_dto import (
    ActiveAbilityDTO,
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    BattleContext,
    BattleMeta,
    CombatActionDTO,
)


class CombatDataService:
    """
    CombatDataService (RBC v3.0).
    Единая точка доступа к данным боя для Коллектора и Исполнителя.
    Использует CombatManager для низкоуровневых операций.
    """

    def __init__(self, combat_manager: CombatManager):
        self.combat_manager = combat_manager

    # ==========================================================================
    # 1. МЕТОДЫ ДЛЯ КОЛЛЕКТОРА (LIGHTWEIGHT)
    # ==========================================================================

    async def get_battle_meta(self, session_id: str) -> BattleMeta | None:
        """Загружает только мета-данные боя."""
        meta_raw = await self.combat_manager.get_rbc_session_meta(session_id)
        if not meta_raw:
            return None
        return self._parse_meta(meta_raw)

    async def get_intent_moves(self, session_id: str, char_ids: list[int]) -> dict[int, Any]:
        """
        Пакетная загрузка намерений (пуль) игроков.
        Возвращает словарь {char_id: moves_dict}.
        """
        return await self.combat_manager.get_moves_batch(session_id, char_ids)

    async def get_targets(self, session_id: str) -> dict[int, list[int]]:
        """
        Загружает очереди целей всех участников.
        Возвращает {char_id: [target_id, ...]}.
        """
        targets_map, _ = await self.combat_manager.load_snapshot_data_batch(session_id, [])
        return targets_map

    async def check_intent_exists(self, session_id: str, char_id: int) -> bool:
        """Быстрая проверка наличия хода."""
        return await self.combat_manager.check_move_exists(session_id, char_id)

    async def push_actions_to_queue(self, session_id: str, actions: list[CombatActionDTO]) -> None:
        """Запись резолвленных задач в системную очередь q:actions."""
        if not actions:
            return

        actions_json = [a.model_dump_json() for a in actions]
        await self.combat_manager.push_actions_batch(session_id, actions_json)

    async def transfer_actions(self, session_id: str, actions: list[CombatActionDTO]) -> None:
        """
        Атомарный перенос действий: Push в очередь + Delete из moves.
        """
        if not actions:
            return

        actions_json = []
        deletes = []

        for action in actions:
            # 1. JSON для очереди
            actions_json.append(action.model_dump_json())

            # 2. Данные для удаления (Source Move)
            deletes.append(
                {"char_id": action.move.char_id, "strategy": action.move.strategy, "move_id": action.move.move_id}
            )

            # 3. Если это Exchange, удаляем и Partner Move
            if action.partner_move:
                deletes.append(
                    {
                        "char_id": action.partner_move.char_id,
                        "strategy": action.partner_move.strategy,
                        "move_id": action.partner_move.move_id,
                    }
                )

        await self.combat_manager.transfer_intents_to_actions(session_id, actions_json, deletes)

    # ==========================================================================
    # 2. МЕТОДЫ ДЛЯ ИСПОЛНИТЕЛЯ (HEAVYWEIGHT)
    # ==========================================================================

    async def load_battle_context(self, session_id: str) -> BattleContext | None:
        """
        Полная пакетная загрузка контекста и всей очереди задач.
        Использует CombatManager.load_full_context_data.
        """
        # 1. Meta
        meta_raw = await self.combat_manager.get_rbc_session_meta(session_id)
        if not meta_raw:
            return None
        meta = self._parse_meta(meta_raw)

        # 2. Actors List
        all_actor_ids = []
        for team_ids in meta.teams.values():
            all_actor_ids.extend(team_ids)

        # 3. Full Load via Manager
        structured_data = await self.combat_manager.load_full_context_data(session_id, all_actor_ids)

        actors_map = {}
        moves_cache = {}

        for cid, data in structured_data.items():
            if cid == "global_queue":
                continue

            if not data["state"]:
                continue

            # Build Snapshot
            actors_map[cid] = self._build_snapshot(
                cid,
                self._find_team(cid, meta.teams),
                data["state"],
                data["raw"],
                data["loadout"],
                data["meta"],
                data["abilities"],
                data["xp"],
            )

            # Cache Move
            if data["move"]:
                moves_cache[cid] = data["move"]

        return BattleContext(
            session_id=session_id, meta=meta, actors=actors_map, moves_cache=moves_cache, pending_logs=[]
        )

    async def load_snapshot_context(self, session_id: str) -> BattleContext | None:
        """
        Легкая загрузка для UI (без XP и Queue).
        Использует тот же механизм, что и load_battle_context, но фильтрует лишнее на уровне DTO.
        (Для оптимизации можно сделать отдельный метод в Manager, но пока так).
        """
        return await self.load_battle_context(session_id)

    async def commit_session(self, ctx: BattleContext, processed_action_ids: list[str]) -> None:
        """
        Атомарное сохранение изменений.
        Использует CombatManager.commit_battle_results.
        """
        updates = {}

        # 1. Prepare Updates
        for cid, actor in ctx.actors.items():
            actor_updates = {}

            # State (Always) - сохраняем только state поля из meta
            # Важно: ActorMetaDTO содержит и meta и state.
            # В Redis мы пишем в разные ключи, но здесь у нас единый объект.
            # CombatManager ожидает "state" как словарь с hp, en и т.д.

            state_dict = {
                "hp": actor.meta.hp,
                "max_hp": actor.meta.max_hp,
                "en": actor.meta.en,
                "max_en": actor.meta.max_en,
                "tactics": actor.meta.tactics,
                "is_dead": int(actor.meta.is_dead),
                "tokens": actor.meta.tokens,
            }
            actor_updates["state"] = state_dict

            # Active Abilities (Always rewrite list)
            actor_updates["abilities"] = [a.model_dump() for a in actor.active_abilities]

            # XP Buffer (Always rewrite)
            actor_updates["xp"] = actor.xp_buffer

            # Raw Temp (Only if dirty - logic to be added, now always)
            # actor_updates["raw_temp"] = actor.raw.temp

            updates[cid] = actor_updates

        # 2. Prepare Logs
        logs = [json.dumps(entry) for entry in ctx.pending_logs]

        # 3. Commit via Manager
        await self.combat_manager.commit_battle_results(ctx.session_id, updates, logs, len(processed_action_ids))

    # ==========================================================================
    # 3. HELPERS
    # ==========================================================================

    def _parse_meta(self, raw: dict) -> BattleMeta:
        def d(k):
            return raw.get(k.encode()) if isinstance(k, str) else raw.get(k)

        return BattleMeta(
            active=int(d("active") or 1),
            step_counter=int(d("step_counter") or 0),
            active_actors_count=0,
            teams=json.loads(d("teams") or "{}"),
            actors_info=json.loads(d("actors_info") or "{}"),
            dead_actors=json.loads(d("dead_actors") or "[]"),
            last_activity_at=int(d("last_activity_at") or 0),
            battle_type=(d("battle_type") or b"standard").decode(),
            location_id=(d("location_id") or b"unknown").decode(),
        )

    def _build_snapshot(self, cid, team, r_state, r_raw, r_loadout, r_meta, r_active, r_xp) -> ActorSnapshot:
        meta_dict = r_meta or {}

        meta = ActorMetaDTO(
            id=cid,
            name=meta_dict.get("name", "Unknown"),
            type=meta_dict.get("type", "unknown"),
            team=team,
            template_id=meta_dict.get("template_id"),
            is_ai=meta_dict.get("is_ai", False),
            # State fields
            hp=int(r_state.get(b"hp", 0)),
            max_hp=int(r_state.get(b"max_hp", 0)),
            en=int(r_state.get(b"en", 0)),
            max_en=int(r_state.get(b"max_en", 0)),
            tactics=int(r_state.get(b"tactics", 0)),
            is_dead=bool(int(r_state.get(b"is_dead", 0))),
            tokens=json.loads(r_state.get(b"tokens") or "{}"),
        )

        raw_dict = r_raw or {}
        loadout_dict = r_loadout or {}

        merged_raw = {
            "attributes": raw_dict.get("attributes", {}),
            "modifiers": raw_dict.get("modifiers", {}),
            # "temp": raw_dict.get("temp", {}), # ActorRawDTO не имеет поля temp в определении выше, проверим
        }

        loadout = ActorLoadoutDTO(
            layout=loadout_dict.get("equipment_layout", {}),
            belt=loadout_dict.get("belt", []),
            known_abilities=loadout_dict.get("known_abilities", []),
            tags=loadout_dict.get("tags", []),
        )

        return ActorSnapshot(
            meta=meta,
            raw=ActorRawDTO(**merged_raw),
            loadout=loadout,
            active_abilities=[ActiveAbilityDTO(**a) for a in (r_active or [])],
            xp_buffer=r_xp or {},
        )

    def _find_team(self, cid: int, teams: dict) -> str:
        for t_name, members in teams.items():
            if cid in members:
                return t_name
        return "neutral"
