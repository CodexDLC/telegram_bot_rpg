import json

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories import get_inventory_repo, get_wallet_repo
from apps.common.schemas_dto.inventory_dto import InventorySessionDTO, WalletDTO
from apps.common.schemas_dto.item_dto import InventoryItemDTO, InventoryItemTypeAdapter
from apps.common.services.redis.redis_service import RedisService


class InventorySessionManager:
    """
    Менеджер сессии инвентаря.
    Отвечает за загрузку, кэширование и сохранение состояния инвентаря (Предметы + Кошелек).
    Реализует паттерн Write-Behind (отложенная запись) с использованием Dirty Flags.
    """

    SESSION_TTL = 3600  # 1 час

    def __init__(self, redis_service: RedisService, session: AsyncSession):
        self.redis = redis_service
        self.session = session
        self.inventory_repo = get_inventory_repo(session)
        self.wallet_repo = get_wallet_repo(session)

    def _get_session_key(self, char_id: int) -> str:
        return f"inventory:session:{char_id}"

    def _get_dirty_items_key(self, char_id: int) -> str:
        return f"inventory:session:{char_id}:dirty_items"

    def _get_deleted_items_key(self, char_id: int) -> str:
        return f"inventory:session:{char_id}:deleted_items"

    def _get_dirty_wallet_key(self, char_id: int) -> str:
        return f"inventory:session:{char_id}:dirty_wallet"

    async def load_session(self, char_id: int) -> InventorySessionDTO:
        """
        Загружает сессию инвентаря.
        1. Пробует загрузить из Redis.
        2. Если нет -> грузит из БД, формирует DTO, кэширует в Redis.
        """
        key = self._get_session_key(char_id)

        # 1. Попытка загрузки из Redis
        raw_data = await self.redis.get_all_hash(key)
        if raw_data:
            try:
                # Продлеваем жизнь сессии при чтении (LRU)
                await self.redis.expire(key, self.SESSION_TTL)
                return self._parse_redis_data(raw_data)
            except Exception as e:  # noqa: BLE001
                log.error(f"InvSession | Corrupted cache for char_id={char_id}: {e}. Reloading from DB.")
                await self.redis.delete_key(key)
                await self.redis.delete_key(self._get_dirty_items_key(char_id))
                await self.redis.delete_key(self._get_dirty_wallet_key(char_id))

        # 2. Загрузка из БД (Cache Miss)
        log.debug(f"InvSession | Cache MISS char_id={char_id}. Loading from DB...")

        # 2.1 Загружаем предметы
        items_list = await self.inventory_repo.get_all_items(char_id)
        items_dict = {item.inventory_id: item for item in items_list}

        # 2.2 Загружаем кошелек
        wallet_orm = await self.wallet_repo.get_wallet(char_id)
        if not wallet_orm:
            wallet_dto = WalletDTO()
        else:
            wallet_dto = WalletDTO(
                currency=wallet_orm.currency or {},
                resources=wallet_orm.resources or {},
                components=wallet_orm.components or {},
            )

        # 2.3 Собираем DTO
        session_dto = InventorySessionDTO(items=items_dict, wallet=wallet_dto, stats={})

        # 3. Сохраняем в Redis
        await self._save_session_to_redis(char_id, session_dto)

        return session_dto

    def _parse_redis_data(self, raw_data: dict[str, str]) -> InventorySessionDTO:
        """Парсит плоский Hash Redis обратно в структуру DTO."""
        items = {}
        wallet = WalletDTO()
        stats = {}

        for k, v in raw_data.items():
            if k.startswith("item:"):
                try:
                    item_data = json.loads(v)
                    item_dto = InventoryItemTypeAdapter.validate_python(item_data)
                    items[item_dto.inventory_id] = item_dto
                except Exception as e:  # noqa: BLE001
                    log.warning(f"InvSession | Failed to parse item {k}: {e}")

            elif k.startswith("currency:"):
                key_name = k.split(":", 1)[1]
                wallet.currency[key_name] = int(v)

            elif k.startswith("resource:"):
                key_name = k.split(":", 1)[1]
                wallet.resources[key_name] = int(v)

            elif k.startswith("component:"):
                key_name = k.split(":", 1)[1]
                wallet.components[key_name] = int(v)

            elif k.startswith("meta:"):
                key_name = k.split(":", 1)[1]
                try:
                    stats[key_name] = json.loads(v)
                except:  # noqa: E722
                    stats[key_name] = v

        return InventorySessionDTO(items=items, wallet=wallet, stats=stats)

    async def _save_session_to_redis(self, char_id: int, dto: InventorySessionDTO):
        """Сериализует DTO в плоский Hash и сохраняет в Redis."""
        key = self._get_session_key(char_id)
        data = {}

        for item_id, item in dto.items.items():
            data[f"item:{item_id}"] = item.model_dump_json()

        for k, v in dto.wallet.currency.items():
            if v > 0:
                data[f"currency:{k}"] = str(v)

        for k, v in dto.wallet.resources.items():
            if v > 0:
                data[f"resource:{k}"] = str(v)

        for k, v in dto.wallet.components.items():
            if v > 0:
                data[f"component:{k}"] = str(v)

        for k, v in dto.stats.items():
            data[f"meta:{k}"] = json.dumps(v)

        if data:
            await self.redis.set_hash_fields(key, data)
            await self.redis.expire(key, self.SESSION_TTL)

    # --- Методы изменения состояния (Dirty Tracking) ---

    async def update_item(self, char_id: int, item: InventoryItemDTO):
        """
        Обновляет предмет в сессии и помечает его как 'dirty'.
        """
        key = self._get_session_key(char_id)
        field = f"item:{item.inventory_id}"
        value = item.model_dump_json()

        # 1. Обновляем данные
        await self.redis.set_hash_fields(key, {field: value})
        await self.redis.expire(key, self.SESSION_TTL)

        # 2. Добавляем в список измененных
        await self.redis.add_to_set(self._get_dirty_items_key(char_id), str(item.inventory_id))
        await self.redis.expire(self._get_dirty_items_key(char_id), self.SESSION_TTL)

    async def remove_item(self, char_id: int, item_id: int):
        """
        Удаляет предмет из сессии и помечает на удаление в БД.
        """
        key = self._get_session_key(char_id)
        field = f"item:{item_id}"

        # 1. Удаляем из данных
        await self.redis.delete_hash_field(key, field)
        # Продлеваем жизнь сессии
        await self.redis.expire(key, self.SESSION_TTL)

        # 2. Добавляем в список удаленных
        await self.redis.add_to_set(self._get_deleted_items_key(char_id), str(item_id))
        # Убираем из dirty, если он там был
        await self.redis.remove_from_set(self._get_dirty_items_key(char_id), str(item_id))

        await self.redis.expire(self._get_deleted_items_key(char_id), self.SESSION_TTL)

    async def update_resource(self, char_id: int, category: str, res_key: str, amount: int):
        """
        Обновляет ресурс и помечает кошелек как 'dirty'.
        """
        key = self._get_session_key(char_id)
        field = f"{category}:{res_key}"

        # RedisService doesn't have increment_hash_field, so we implement it manually
        current_val_str = await self.redis.get_hash_field(key, field)
        current_val = int(current_val_str) if current_val_str else 0
        new_val = current_val + amount

        if new_val <= 0:
            await self.redis.delete_hash_field(key, field)
        else:
            await self.redis.set_hash_fields(key, {field: str(new_val)})

        await self.redis.expire(key, self.SESSION_TTL)

        # Помечаем кошелек как грязный
        await self.redis.set_value(self._get_dirty_wallet_key(char_id), "1", ttl=self.SESSION_TTL)

    # --- Синхронизация с БД (Flush) ---

    async def flush_session_to_db(self, char_id: int):
        """
        Синхронизирует изменения из Redis в БД.
        Вызывается при закрытии инвентаря или фоновой задачей.
        """
        log.debug(f"InvSession | Flushing session for char_id={char_id}")

        # 1. Обработка удаленных предметов
        deleted_ids = await self.redis.get_set_members(self._get_deleted_items_key(char_id))
        if deleted_ids:
            for item_id_str in deleted_ids:
                try:
                    await self.inventory_repo.delete_item(int(item_id_str))
                except Exception as e:  # noqa: BLE001
                    log.error(f"Flush | Failed to delete item {item_id_str}: {e}")
            await self.redis.delete_key(self._get_deleted_items_key(char_id))

        # 2. Обработка измененных предметов (Dirty Items)
        dirty_ids = await self.redis.get_set_members(self._get_dirty_items_key(char_id))
        if dirty_ids:
            session_key = self._get_session_key(char_id)
            for item_id_str in dirty_ids:
                raw_json = await self.redis.get_hash_field(session_key, f"item:{item_id_str}")
                if raw_json:
                    try:
                        item_data = json.loads(raw_json)
                        item_dto = InventoryItemTypeAdapter.validate_python(item_data)

                        update_data = {
                            "location": item_dto.location,
                            "equipped_slot": item_dto.equipped_slot,
                            "quick_slot_position": item_dto.quick_slot_position,
                            "quantity": item_dto.quantity,
                            "item_data": item_dto.data.model_dump(mode="json"),
                        }
                        await self.inventory_repo.update_fields(item_dto.inventory_id, update_data)
                    except Exception as e:  # noqa: BLE001
                        log.error(f"Flush | Failed to update item {item_id_str}: {e}")

            await self.redis.delete_key(self._get_dirty_items_key(char_id))

        # 3. Обработка кошелька (Dirty Wallet)
        is_wallet_dirty = await self.redis.get_value(self._get_dirty_wallet_key(char_id))
        if is_wallet_dirty:
            raw_data = await self.redis.get_all_hash(self._get_session_key(char_id))
            if raw_data:  # Check if raw_data is not None
                wallet_dto = WalletDTO()

                for k, v in raw_data.items():
                    if k.startswith("currency:"):
                        wallet_dto.currency[k.split(":", 1)[1]] = int(v)
                    elif k.startswith("resource:"):
                        wallet_dto.resources[k.split(":", 1)[1]] = int(v)
                    elif k.startswith("component:"):
                        wallet_dto.components[k.split(":", 1)[1]] = int(v)

                try:
                    # Using update_wallet instead of update_wallet_data
                    await self.wallet_repo.update_wallet(
                        char_id,
                        currency=wallet_dto.currency,
                        resources=wallet_dto.resources,
                        components=wallet_dto.components,
                    )
                    await self.redis.delete_key(self._get_dirty_wallet_key(char_id))
                except Exception as e:  # noqa: BLE001
                    log.error(f"Flush | Failed to update wallet: {e}")

        # Продлеваем жизнь сессии после успешного сохранения
        await self.redis.expire(self._get_session_key(char_id), self.SESSION_TTL)
        log.debug(f"InvSession | Flush complete char_id={char_id}")
