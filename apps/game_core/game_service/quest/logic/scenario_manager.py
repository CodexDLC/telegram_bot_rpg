import json
from typing import Any

from loguru import logger as log

# Предполагаем, что RedisService уже импортирован
from apps.common.services.core_service.redis_service import RedisService


class ScenarioManager:
    """
    Диспетчер данных сценария.
    Управляет импортом/экспортом (World Sync) и состоянием песочницы (Session Context).
    """

    def __init__(self, redis_service: RedisService):
        self.redis = redis_service
        # Маппинг команд на методы RedisService
        self._dispatch_map = {
            "hjson": self._handle_hjson,
            "val": self._handle_val,
            "lpop": self._handle_lpop,
            "rpush": self._handle_rpush,
            "sadd": self._handle_sadd,
        }

    # --- 1. Работа с "Песочницей" (Session Key) ---

    async def get_session_context(self, char_id: int) -> dict[str, Any]:
        """Загружает весь текущий контекст из песочницы Redis, десериализуя JSON-строки."""
        key = f"scen:session:{char_id}:data"
        raw_data = await self.redis.get_all_hash(key)
        if not raw_data:
            return {}

        context = {}
        for k, v in raw_data.items():
            try:
                # Пытаемся десериализовать. Если это не JSON, будет ошибка.
                context[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                # Если не получилось, значит это простое значение.
                # Redis возвращает строки, пытаемся преобразовать в число, если возможно.
                if v.isdigit():
                    context[k] = int(v)
                else:
                    try:
                        context[k] = float(v)
                    except ValueError:
                        context[k] = v  # Оставляем как строку
        return context

    async def save_session_context(self, char_id: int, context: dict[str, Any], ttl: int = 86400):
        """Сохраняет обновленный контекст в песочницу Redis, сериализуя сложные типы."""
        key = f"scen:session:{char_id}:data"
        if not context:
            return

        processed_context = {}
        for k, v in context.items():
            if isinstance(v, (dict, list)):
                processed_context[k] = json.dumps(v)
            else:
                processed_context[k] = v

        await self.redis.set_hash_fields(key, processed_context)
        await self.redis.expire(key, ttl)

    # --- 2. Синхронизация с внешним миром (World Sync) ---

    async def sync_external(self, char_id: int, instructions: dict[str, str], direction: str = "import"):
        """
        Универсальный цикл синхронизации.
        direction='import': Из мира в сессию.
        direction='export': Из сессии в мир.
        """
        session_data = await self.get_session_context(char_id) if direction == "export" else {}
        updates_for_session = {}

        for quest_var, command_str in instructions.items():
            cmd_rendered = command_str.replace("{char_id}", str(char_id))

            if direction == "import":
                val = await self._process_command(cmd_rendered)
                if val is not None:
                    updates_for_session[quest_var] = val
            else:
                val_to_export = session_data.get(quest_var)
                if val_to_export is not None:
                    await self._process_command(cmd_rendered, value=val_to_export)

        if updates_for_session:
            # Обновляем существующий контекст, а не перезаписываем
            current_context = await self.get_session_context(char_id)
            current_context.update(updates_for_session)
            await self.save_session_context(char_id, current_context)

    # --- 3. Универсальный метод работы с ключом (_process_command) ---

    async def _process_command(self, cmd_str: str, value: Any = None) -> Any:
        """
        Парсит 'метод:ключ:путь' и вызывает соответствующий метод RedisService.
        """
        parts = cmd_str.split(":", 2)
        if len(parts) < 2:
            return None

        method, key = parts[0], parts[1]
        path = parts[2] if len(parts) > 2 else None

        handler = self._dispatch_map.get(method)
        if not handler:
            log.error(f"Unknown method '{method}' in command '{cmd_str}'")
            return None

        return await handler(key, path, value)

    # --- Обработчики конкретных типов данных Redis ---

    async def _handle_hjson(self, key: str, path: str | None, value: Any = None) -> Any:
        """Обработка JSON внутри HASH (например, ac:stats.strength)"""
        field = path.split(".")[0] if path else "data"
        sub_key = path.split(".")[1] if path and "." in path else None

        if value is None:  # GET
            data = await self.redis.get_hash_json(key, field)
            return data.get(sub_key) if (data and sub_key) else data
        else:  # SET
            current_data = await self.redis.get_hash_json(key, field) or {}
            if sub_key:
                current_data[sub_key] = value
            else:
                current_data = value
            await self.redis.set_hash_json(key, field, current_data)
            return True

    async def _handle_val(self, key: str, path: str | None, value: Any = None) -> Any:
        """Обработка простых строковых значений"""
        if value is None:
            return await self.redis.get_value(key)
        await self.redis.set_value(key, str(value))
        return True

    async def _handle_lpop(self, key: str, path: str | None, value: Any = None) -> Any:
        """Извлечение из списка"""
        return await self.redis.pop_from_list_left(key)

    async def _handle_rpush(self, key: str, path: str | None, value: Any = None) -> Any:
        """Добавление в список"""
        if value is not None:
            await self.redis.push_to_list(key, str(value))
        return True

    async def _handle_sadd(self, key: str, path: str | None, value: Any = None) -> Any:
        """Добавление в множество"""
        if value is not None:
            await self.redis.add_to_set(key, value)
        return True
