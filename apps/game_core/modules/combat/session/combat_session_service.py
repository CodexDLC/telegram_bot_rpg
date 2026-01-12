# apps/game_core/modules/combats/session/combat_session_service.py
import itertools
import json

from apps.common.schemas_dto.combat_source_dto import CombatDashboardDTO, CombatLogDTO
from apps.common.services.redis.manager.account_manager import AccountManager
from apps.common.services.redis.manager.combat_manager import CombatManager
from apps.common.services.redis.redis_fields import AccountFields as Af
from apps.game_core.modules.combat.dto.combat_internal_dto import (
    ActiveAbilityDTO,
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    BattleContext,
    BattleMeta,
)

# Менеджеры и сервисы
from apps.game_core.modules.combat.session.runtime.combat_turn_manager import CombatTurnManager
from apps.game_core.modules.combat.session.runtime.combat_view_service import CombatViewService


def batched(iterable, n):
    """
    Batch data into tuples of length n. The last batch may be shorter.
    Backport for Python < 3.12.
    """
    it = iter(iterable)
    while batch := list(itertools.islice(it, n)):
        yield batch


class CombatSessionService:
    """
    Facade (v3.0). Скрывает детали боевой сессии от внешних слоев.
    Работает строго по char_id персонажа.
    Отвечает за "легкое" чтение данных для клиента.
    """

    def __init__(
        self,
        account_manager: AccountManager,
        combat_manager: CombatManager,
        turn_manager: CombatTurnManager,
        view_service: CombatViewService,
    ):
        self.account_manager = account_manager
        self.combat_manager = combat_manager
        self.turn_manager = turn_manager
        self.view_service = view_service

    # --- PRIVATE HELPERS ---

    async def _resolve_session_id(self, char_id: int) -> str:
        """Резолвит сессию по персонажу."""
        session_id = await self.account_manager.get_account_field(char_id, Af.COMBAT_SESSION_ID)
        if not session_id:
            raise ValueError(f"Character {char_id} is not in active combats.")
        return str(session_id)

    # --- PUBLIC ACTIONS (Intents) ---

    async def register_move(self, char_id: int, payload: dict) -> CombatDashboardDTO:
        """
        Универсальная точка регистрации намерения.
        Возвращает актуальный снапшот (клиент сам решит, ждать или обновлять UI).
        """
        session_id = await self._resolve_session_id(char_id)

        # 1. Регистрируем ход (Redis + ARQ)
        await self.turn_manager.register_move_request(session_id, char_id, payload)

        # 2. Возвращаем актуальный снапшот
        return await self.get_snapshot(char_id)

    # --- READ MODELS (Lightweight Snapshot) ---

    async def get_snapshot(self, char_id: int) -> CombatDashboardDTO:
        """
        Получить актуальный экран боя.
        Собирает данные напрямую из Redis (без тяжелого ActorManager).
        """
        session_id = await self._resolve_session_id(char_id)

        # 1. Загружаем легкий контекст (2 RTT)
        context = await self._load_snapshot_context(session_id)
        if not context:
            raise ValueError(f"Session {session_id} data not found")

        # 2. Маппинг в DTO
        return self.view_service.build_dashboard_dto_from_context(char_id, context)

    async def get_logs(self, char_id: int, page: int = 0) -> CombatLogDTO:
        """Получить логи боя."""
        session_id = await self._resolve_session_id(char_id)
        raw_logs = await self.combat_manager.get_combat_log_list(session_id)
        return self.view_service.build_logs_dto(raw_logs, page)

    # --- INTERNAL LOADING LOGIC ---

    async def _load_snapshot_context(self, session_id: str) -> BattleContext | None:
        """
        Загружает минимально необходимые данные для UI.
        Meta + Targets + State + Raw(Name/Layout) + Moves + ActiveAbilities.
        """
        # 1. Load Meta (чтобы узнать участников)
        meta_raw = await self.combat_manager.get_rbc_session_meta(session_id)
        if not meta_raw:
            return None

        meta = self._parse_meta(meta_raw)

        all_actor_ids = []
        for team_ids in meta.teams.values():
            all_actor_ids.extend(team_ids)

        # 2. Batch Load via Manager
        targets_map, actors_data_list = await self.combat_manager.load_snapshot_data_batch(session_id, all_actor_ids)

        actors_map = {}
        moves_cache = {}

        # Используем batched для упрощения чтения
        batches = batched(actors_data_list, 5)
        for cid, (res_state, res_meta, res_loadout, res_active, res_moves) in zip(all_actor_ids, batches, strict=False):
            if res_state:
                actors_map[cid] = self._build_light_snapshot(
                    cid, self._find_team(cid, meta.teams), res_state, res_meta, res_loadout, res_active
                )

            if res_moves:
                moves_cache[cid] = res_moves

        return BattleContext(
            session_id=session_id,
            meta=meta,
            actors=actors_map,
            moves_cache=moves_cache,
            targets=targets_map,
            pending_logs=[],
        )

    # --- HELPERS ---

    def _parse_meta(self, raw: dict) -> BattleMeta:
        def d(k):
            return raw.get(k.encode()) if isinstance(k, str) else raw.get(k)

        return BattleMeta(
            active=int(d("active") or 1),
            step_counter=int(d("step_counter") or 0),
            active_actors_count=0,  # Не важно для UI
            teams=json.loads(d("teams") or "{}"),
            actors_info=json.loads(d("actors_info") or "{}"),
            battle_type=(d("battle_type") or b"standard").decode(),
            location_id=(d("location_id") or b"unknown").decode(),
        )

    def _build_light_snapshot(self, cid, team, r_state, r_meta, r_loadout, r_active) -> ActorSnapshot:
        """Собирает облегченный снапшот (без полной математики)."""

        # Meta + State (Merged)
        # В Redis state и meta могут быть разделены, но мы объединяем их в ActorMetaDTO
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
            max_hp=int(r_state.get(b"max_hp", 100)),
            en=int(r_state.get(b"en", 0)),
            max_en=int(r_state.get(b"max_en", 100)),
            tactics=int(r_state.get(b"tactics", 0)),
            is_dead=bool(int(r_state.get(b"is_dead", 0))),
            tokens=json.loads(r_state.get(b"tokens") or "{}"),
        )

        # Raw (Fake/Partial)
        loadout_dict = r_loadout or {}

        raw_dto = ActorRawDTO(
            attributes={},  # Не нужно для UI
            modifiers={},  # Не нужно для UI
        )

        # Loadout
        loadout_dto = ActorLoadoutDTO(
            layout=loadout_dict.get("equipment_layout", {}),
            known_abilities=loadout_dict.get("known_abilities", []),
            belt=[],
            tags=[],
        )

        return ActorSnapshot(
            meta=meta,
            raw=raw_dto,
            loadout=loadout_dto,
            active_abilities=[ActiveAbilityDTO(**a) for a in (r_active or [])],
            xp_buffer={},  # Не нужно
        )

    def _find_team(self, cid: int, teams: dict) -> str:
        for t_name, members in teams.items():
            if cid in members:
                return t_name
        return "neutral"

    # --- LIFECYCLE ---

    async def link_players_to_session(self, char_ids: list[int], session_id: str) -> None:
        await self.account_manager.bulk_link_combat_session(char_ids, session_id)

    async def unlink_players_from_session(self, char_ids: list[int]) -> None:
        await self.account_manager.bulk_unlink_combat_session(char_ids)
