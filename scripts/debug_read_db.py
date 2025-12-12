import asyncio
import datetime
import json
import os
import sys
from textwrap import dedent

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# ==============================================================================
# НАСТРОЙКИ ОКРУЖЕНИЯ (FIXED PATHS)
# ==============================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(current_dir)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")  # Папка для логов
DB_PATH = os.path.join(DATA_DIR, "game_db.db")

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Создаем папку логов, если нет
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR, exist_ok=True)

clean_db_path = DB_PATH.replace("\\", "/")
DB_URL = f"sqlite+aiosqlite:///{clean_db_path}"
REDIS_URL = "redis://localhost:6379"

try:
    from apps.common.core.config import settings

    if settings.REDIS_URL:
        REDIS_URL = settings.REDIS_URL
except ImportError:
    pass


# ==============================================================================
# ИНСТРУМЕНТАРИЙ
# ==============================================================================


class UniversalDebugger:
    def __init__(self):
        if not os.path.exists(DB_PATH):
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Файл БД не найден: {DB_PATH}")
            sys.exit(1)

        self.engine = create_async_engine(DB_URL, echo=False)
        self.async_session = sessionmaker(bind=self.engine, class_=AsyncSession, expire_on_commit=False)
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)

    async def close(self):
        await self.engine.dispose()
        await self.redis_client.close()

    def _safe_json(self, val):
        """Безопасный парсинг JSON для вывода."""
        if isinstance(val, (dict, list)):
            return val
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val

    # --- МЕТОДЫ SQLite (VIEW) ---

    async def get_world_stats(self):
        async with self.async_session() as session:
            try:
                r_count = (await session.execute(text("SELECT COUNT(*) FROM world_regions"))).scalar()
                z_count = (await session.execute(text("SELECT COUNT(*) FROM world_zones"))).scalar()
                n_count = (await session.execute(text("SELECT COUNT(*) FROM world_grid"))).scalar()
                active_n = (await session.execute(text("SELECT COUNT(*) FROM world_grid WHERE is_active = 1"))).scalar()

                print(
                    dedent(f"""
                📊 СТАТИСТИКА МИРА:
                -------------------
                🌍 Регионы: {r_count}
                🏙  Зоны:    {z_count}
                📦 Клетки:  {n_count}
                🔥 Активные: {active_n}
                """)
                )
            except SQLAlchemyError as e:
                print(f"❌ Ошибка: {e}")

    async def show_real_active_zones(self):
        sql = """
        SELECT zone_id, COUNT(*) as active_cells 
        FROM world_grid 
        WHERE is_active = 1 
        GROUP BY zone_id 
        ORDER BY zone_id ASC
        """
        async with self.async_session() as session:
            rows = (await session.execute(text(sql))).fetchall()
            print("\n🔥 АКТИВНЫЕ ЗОНЫ:")
            print(f"{'ZONE ID':<20} | {'CELLS':<10}")
            print("-" * 35)
            if not rows:
                print("   (Пусто)")
            for row in rows:
                print(f"{row[0]:<20} | {row[1]:<10}")

    async def inspect_node(self):
        try:
            x, y = map(int, input("Введите X Y: ").split())
        except ValueError:
            print("❌ Ошибка ввода.")
            return

        sql = "SELECT zone_id, terrain_type, is_active, flags, content, services FROM world_grid WHERE x=:x AND y=:y"
        async with self.async_session() as session:
            row = (await session.execute(text(sql), {"x": x, "y": y})).fetchone()
            if not row:
                print("❌ Клетка не найдена.")
                return

            print(f"\n🔍 ({x}, {y}) | Zone: {row[0]} | Active: {bool(row[2])}")
            print(f"   Terrain: {row[1]}")
            print(f"   Flags: {json.dumps(self._safe_json(row[3]), indent=2, ensure_ascii=False)}")
            print(f"   Content: {json.dumps(self._safe_json(row[4]), indent=2, ensure_ascii=False)}")

    # --- МЕТОДЫ ЭКСПОРТА (НОВЫЕ) ---

    async def export_active_to_file(self):
        """Выгружает ВСЕ активные клетки в файл."""
        filename = f"dump_active_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(LOGS_DIR, filename)

        sql = """
        SELECT x, y, zone_id, terrain_type, content, flags 
        FROM world_grid 
        WHERE is_active = 1 
        ORDER BY zone_id, x, y
        """

        print("⏳ Выгрузка данных...")
        async with self.async_session() as session:
            rows = (await session.execute(text(sql))).fetchall()

            if not rows:
                print("⚠️ Нет активных клеток для выгрузки.")
                return

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"=== ACTIVE CELLS DUMP ({len(rows)}) ===\n")
                current_zone = None
                for row in rows:
                    if row[2] != current_zone:
                        current_zone = row[2]
                        f.write(f"\n{'=' * 20}\n ZONE: {current_zone}\n{'=' * 20}\n")

                    content = self._safe_json(row[4])
                    title = content.get("title", "No Title") if isinstance(content, dict) else "Raw"

                    f.write(f"[{row[0]}, {row[1]}] {row[3]} | {title}\n")
                    f.write(f"   Flags: {self._safe_json(row[5])}\n")
                    f.write(f"   Content: {json.dumps(content, ensure_ascii=False)}\n")
                    f.write("-" * 40 + "\n")

        print(f"✅ Успешно сохранено в: {filepath}")

    async def export_zone_to_file(self):
        """Выгружает ВСЮ зону (даже неактивные клетки) в файл."""
        zone_id = input("Введите ID зоны (например D4_1_1): ").strip()
        filename = f"dump_zone_{zone_id}.txt"
        filepath = os.path.join(LOGS_DIR, filename)

        sql = """
        SELECT x, y, terrain_type, is_active, content, flags 
        FROM world_grid 
        WHERE zone_id = :zid 
        ORDER BY x, y
        """

        async with self.async_session() as session:
            rows = (await session.execute(text(sql), {"zid": zone_id})).fetchall()

            if not rows:
                print(f"⚠️ Зона {zone_id} не найдена или пуста.")
                return

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"=== ZONE DUMP: {zone_id} ({len(rows)} cells) ===\n")
                for row in rows:
                    status = "🔥 ACTIVE" if row[3] else "💤 SLEEP"
                    content = self._safe_json(row[4])

                    f.write(f"\n[{row[0]}, {row[1]}] {row[2]} ({status})\n")
                    f.write(f"   Flags: {self._safe_json(row[5])}\n")
                    f.write(f"   Content: {json.dumps(content, ensure_ascii=False)}\n")

        print(f"✅ Успешно сохранено в: {filepath}")

    async def execute_raw_sql(self):
        query = input("\nSQL > ")
        if not query:
            return
        async with self.async_session() as session:
            try:
                res = await session.execute(text(query))
                if query.strip().upper().startswith("SELECT"):
                    for r in res.fetchall()[:20]:
                        print(r)
                else:
                    await session.commit()
                    print("✅ Done.")
            except SQLAlchemyError as e:
                print(f"❌ Error: {e}")

    async def inspect_redis(self):
        keys = await self.redis_client.keys("*")
        print(f"🔴 Redis Keys: {len(keys)}")
        # (Упростил вывод для краткости, функционал тот же)


async def main_menu():
    debugger = UniversalDebugger()
    while True:
        print("\n==================================")
        print("🛠  UNIVERSAL DB INSPECTOR v3.0")
        print("==================================")
        print("[1] 📊 Статистика мира")
        print("[2] 🔥 Активные зоны (Список)")
        print("[3] 🔍 Инспекция клетки (X Y)")
        print("[4] ⌨️  SQL Commander")
        print("[5] 🔴 Redis Inspector")
        print("-" * 34)
        print("[6] 💾 Экспорт ВСЕХ активных (в файл)")
        print("[7] 📂 Экспорт КОНКРЕТНОЙ зоны (в файл)")
        print("[0] 🚪 Выход")

        c = input("Выбор: ")
        if c == "1":
            await debugger.get_world_stats()
        elif c == "2":
            await debugger.show_real_active_zones()
        elif c == "3":
            await debugger.inspect_node()
        elif c == "4":
            await debugger.execute_raw_sql()
        elif c == "5":
            await debugger.inspect_redis()
        elif c == "6":
            await debugger.export_active_to_file()
        elif c == "7":
            await debugger.export_zone_to_file()
        elif c == "0":
            await debugger.close()
            break


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main_menu())
