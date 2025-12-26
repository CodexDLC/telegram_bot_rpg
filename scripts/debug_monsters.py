import asyncio
import json
import os
import sys
import uuid
from datetime import datetime

# Добавляем корневую директорию в путь, чтобы видеть пакеты apps
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402

from apps.common.database.model_orm.monster import GeneratedMonsterORM  # noqa: E402

# Импорты проекта
# ИСПОЛЬЗУЕМ ПРАВИЛЬНЫЙ ИМПОРТ СЕССИИ
from apps.common.database.session import async_session_factory  # noqa: E402


class AlchemyEncoder(json.JSONEncoder):
    """Специальный энкодер для UUID и Datetime из алхимии."""

    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def model_to_dict(obj):
    """Превращает ORM модель в словарь, исключая служебные поля SQLAlchemy."""
    if not obj:
        return None

    data = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        data[column.name] = value
    return data


async def main():
    print("🔌 Подключение к базе данных...")

    # ИСПОЛЬЗУЕМ async_session_factory ВМЕСТО async_session_maker
    async with async_session_factory() as session:
        # Запрашиваем монстров вместе с их кланами
        # Берем последние 5 добавленных
        stmt = (
            select(GeneratedMonsterORM)
            .options(selectinload(GeneratedMonsterORM.clan))
            .order_by(GeneratedMonsterORM.id.desc())
            .limit(5)
        )

        result = await session.execute(stmt)
        monsters = result.scalars().all()

        if not monsters:
            print("❌ В базе данных нет сгенерированных монстров.")
            return

        print(f"✅ Найдено монстров: {len(monsters)}\n")

        for i, monster in enumerate(monsters, 1):
            monster_dict = model_to_dict(monster)
            clan_dict = model_to_dict(monster.clan)

            # Собираем красивый объект для вывода
            full_data = {
                "MONSTER_INFO": {
                    "name": monster.name_ru,
                    "role": monster.role,
                    "threat": monster.threat_rating,
                    "variant_key": monster.variant_key,
                    "SCALED_STATS (База для калькулятора)": monster.scaled_base_stats,
                    "LOADOUT (Экипировка)": monster.loadout_ids,
                    "SKILLS": monster.skills_snapshot,
                    "STATE": monster.current_state,
                },
                "CLAN_INFO": {
                    "family": clan_dict.get("family_id"),
                    "tier": clan_dict.get("tier"),
                    "tags": clan_dict.get("raw_tags"),
                },
                "RAW_DB_DATA": monster_dict,  # Полный сырой дамп
            }

            print(f"--- МОНСТР #{i} [{monster.name_ru}] ---")
            print(json.dumps(full_data, cls=AlchemyEncoder, indent=4, ensure_ascii=False))
            print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    # Для Windows может потребоваться установка политики цикла событий
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Скрипт остановлен.")
