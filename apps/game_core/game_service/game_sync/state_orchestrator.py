# import json
#
# from loguru import logger as log
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from apps.common.database.repositories import (
#     get_character_repo,
#     get_inventory_repo,
#
#     get_symbiote_repo,
#     get_wallet_repo,
# )
# from apps.common.services.core_service.manager.account_manager import AccountManager
#
#
# class GameStateOrchestrator:
#     """
#     Главный оркестратор состояния игрока.
#     Управляет жизненным циклом "Ядра Состояния" (ac:{char_id}) и делегирует
#     управление сессиями (бой, инвентарь, сценарий) соответствующим сервисам.
#     """
#
#     def __init__(self, session: AsyncSession, account_manager: AccountManager):
#         self.session = session
#         self.am = account_manager
#
#         # Репозитории
#         self.char_repo = get_character_repo(session)
#         self.stats_repo = get_character_stats_repo(session)
#         self.symbiote_repo = get_symbiote_repo(session)
#         self.wallet_repo = get_wallet_repo(session)
#         self.inventory_repo = get_inventory_repo(session)
#
#         # TODO: Сюда нужно будет инжектить оркестраторы сессий (Combat, Inventory, Scenario)
#         # self.combat_orchestrator = ...
#         # self.scenario_sync = ...
#
#     async def restore_full_state(self, char_id: int) -> None:
#         """
#         Восстанавливает полное состояние игрока из БД в Redis (Ядро).
#         Если игрок находится в активной сессии (бой, сценарий), пытается восстановить и её.
#         """
#         log.info(f"GameStateOrchestrator | action=restore_full_state char_id={char_id}")
#
#         # 1. Загрузка данных из БД
#         char_data = await self.char_repo.get_character(char_id)
#         if not char_data:
#             log.error(f"GameStateOrchestrator | Character not found char_id={char_id}")
#             return
#
#         stats = await self.stats_repo.get_stats(char_id)
#         symbiote = await self.symbiote_repo.get_symbiote(char_id)
#         wallet = await self.wallet_repo.get_wallet(char_id)
#
#         # 2. Формирование Ядра (Core Data)
#         core_data = {
#             # FSM State
#             "state": char_data.game_stage,
#             "prev_state": getattr(char_data, "prev_game_stage", "") or "",
#
#             # Navigation
#             "location": {
#                 "current": getattr(char_data, "location_id", None),
#                 "prev": getattr(char_data, "prev_location_id", None)
#             },
#
#             # Bio
#             "bio": {
#                 "name": char_data.name,
#                 "gender": char_data.gender,
#                 "created_at": str(char_data.created_at)
#             },
#
#             # Stats
#             "stats": stats.model_dump() if stats else {},
#
#             # Symbiote
#             "symbiote": {
#                 "name": symbiote.symbiote_name if symbiote else "Unknown",
#                 "rank": symbiote.gift_rank if symbiote else 0,
#                 "gift_id": symbiote.gift_id if symbiote else None,
#                 "xp": symbiote.gift_xp if symbiote else 0
#             },
#             "symbiote_res": symbiote.elements_resonance if symbiote else {},
#
#             # Wallet
#             "wallet": {
#                 "currency": wallet.currency if wallet else {},
#                 "resources": wallet.resources if wallet else {},
#                 "components": wallet.components if wallet else {}
#             },
#
#             # Vitals (Расчетные, пока дефолт)
#             # TODO: В будущем можно брать из БД, если решим сохранять
#             "vitals": {
#                 "hp": {"current": 100, "max": 100}, # Заглушка, нужен калькулятор
#                 "mp": {"current": 50, "max": 50},
#                 "stamina": {"current": 100, "max": 100},
#                 "last_regen": 0
#             },
#
#             # Sessions (Ссылки)
#             # Если в БД есть активный сценарий, нужно найти его ID.
#             # Пока считаем, что если state == 'scenario', то ID где-то есть (или восстановим).
#             "combat_session_id": "",
#             "scenario_session_id": "", # TODO: Восстановить из таблицы сценариев
#             "inventory_session_id": ""
#         }
#
#         # 3. Запись в Redis
#         await self.am.create_account(char_id, core_data)
#
#         # 4. Восстановление сессий (Делегирование)
#         # if core_data["state"] == "combat":
#         #     await self.combat_orchestrator.restore_session(char_id)
#         # elif core_data["state"] == "scenario":
#         #     await self.scenario_sync.restore_session(char_id)
#
#         log.info(f"GameStateOrchestrator | status=success char_id={char_id}")
#
#     async def backup_full_state(self, char_id: int) -> None:
#         """
#         Сохраняет состояние из Redis в БД (Бэкап).
#         Сохраняет Ядро и делегирует сохранение активных сессий.
#         """
#         log.info(f"GameStateOrchestrator | action=backup_full_state char_id={char_id}")
#
#         # 1. Чтение Redis
#         ac_data = await self.am.get_account_data(char_id)
#         if not ac_data:
#             log.warning(f"GameStateOrchestrator | No redis data found for char_id={char_id}")
#             return
#
#         # Десериализация (вручную или через хелперы, если бы они возвращали dict)
#         # Тут проще работать с сырыми данными или использовать get_account_json для каждого поля
#         # Но для скорости возьмем все и распарсим то, что нужно.
#
#         try:
#             state = ac_data.get("state")
#             prev_state = ac_data.get("prev_state")
#
#             location_raw = ac_data.get("location")
#             location = json.loads(location_raw) if location_raw else {}
#
#             # stats_raw = ac_data.get("stats")
#             # stats = json.loads(stats_raw) if stats_raw else {}
#
#             symbiote_raw = ac_data.get("symbiote")
#             symbiote = json.loads(symbiote_raw) if symbiote_raw else {}
#
#             symbiote_res_raw = ac_data.get("symbiote_res")
#             symbiote_res = json.loads(symbiote_res_raw) if symbiote_res_raw else {}
#
#             wallet_raw = ac_data.get("wallet")
#             wallet = json.loads(wallet_raw) if wallet_raw else {}
#
#             # 2. Сохранение Ядра в БД
#
#             # Character (State & Location)
#             # В ICharactersRepo нет update_state_and_location, используем update_character_game_stage и update_dynamic_state
#             # Но update_dynamic_state есть только в ORM реализации, а не в интерфейсе.
#             # Для простоты пока используем update_character_game_stage, а локацию пропустим или добавим метод в интерфейс.
#             # В данном случае, так как мы работаем с интерфейсом, мы ограничены им.
#             # Если нужно обновить локацию, нужно добавить метод в интерфейс.
#             # Пока что обновим только стадию.
#             if state:
#                 await self.char_repo.update_character_game_stage(char_id, str(state))
#
#             # Stats
#             # TODO: Нужен метод update_stats в репозитории, принимающий dict
#             # await self.stats_repo.update_stats(char_id, stats)
#
#             # Symbiote
#             if symbiote:
#                 await self.symbiote_repo.update_progress(char_id, symbiote.get("xp", 0), symbiote.get("rank", 1))
#                 # Имя и Дар обновляются редко, но можно добавить
#
#             if symbiote_res:
#                 await self.symbiote_repo.update_elements_resonance(char_id, symbiote_res)
#
#             # Wallet
#             if wallet:
#                 # В IWalletRepo нет update_wallet, есть add/remove.
#                 # Это сложнее. Пока пропустим или нужно переделать логику.
#                 # Для MVP можно предположить, что кошелек обновляется атомарно при транзакциях.
#                 pass
#
#             # 3. Бэкап сессий (Делегирование)
#             # scenario_id = ac_data.get("scenario_session_id")
#             # if scenario_id:
#             #     await self.scenario_sync.backup_active_session(char_id, ...)
#
#         except Exception as e:  # noqa: BLE001
#             log.exception(f"GameStateOrchestrator | Backup failed for char_id={char_id}: {e}")
