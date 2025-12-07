import asyncio
import os
import sys

# Добавляем корень проекта в путь, чтобы видеть app/database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger as log

from app.resources.game_data.world_config import HUB_CENTER, SECTOR_ROWS, SECTOR_SIZE, WORLD_HEIGHT, WORLD_WIDTH
from app.services.game_service.world.threat_service import ThreatService
from database.model_orm.world import WorldGrid, WorldSector
from database.session import async_session_factory


async def seed_world():
    log.info("🌍 World Seeding started...")

    async with async_session_factory() as session:
        # 1. Создаем Сектора (Config)
        # 7x7 = 49 секторов
        sectors_data = []
        for _r_idx, row_char in enumerate(SECTOR_ROWS):
            for c_idx in range(1, 8):
                sec_id = f"{row_char}{c_idx}"
                # Простая логика биомов для старта (можно усложнить)
                biome = "wasteland"
                if sec_id == "D4":
                    biome = "hub"
                elif row_char == "A":
                    biome = "ice"
                elif row_char == "G":
                    biome = "fire"

                sectors_data.append(
                    WorldSector(
                        id=sec_id,
                        tier=1,  # Заглушка, реальный тир будет в клетках
                        biome_id=biome,
                        anchor_type="HUB" if sec_id == "D4" else "WILD",
                    )
                )

        # Upsert секторов (чтобы не падать при повторном запуске)
        for sec in sectors_data:
            await session.merge(sec)
        await session.commit()
        log.info("✅ Sectors created.")

        # 2. Создаем Матрицу Клеток (11,025 шт)
        grid_batch = []
        for x in range(WORLD_WIDTH):
            for y in range(WORLD_HEIGHT):
                # Вычисляем ID сектора: x // 15, y // 15
                col = (x // SECTOR_SIZE) + 1
                row_char = SECTOR_ROWS[y // SECTOR_SIZE]
                sec_id = f"{row_char}{col}"

                # Считаем угрозу
                threat_val = ThreatService.calculate_threat(x, y)
                tier = ThreatService.get_tier_from_threat(threat_val)

                # Флаги
                flags = {
                    "threat_val": round(threat_val, 3),
                    "threat_tier": tier,
                    "latent_rift_id": None,  # Пока пусто, заполнится квестом
                }

                # Определяем активность (Хаб 5x5)
                is_active = False
                content = None

                # Хаб D4 (центр 52:52, радиус 2 => 50..54)
                if abs(x - HUB_CENTER["x"]) <= 2 and abs(y - HUB_CENTER["y"]) <= 2:
                    is_active = True
                    flags["is_safe_zone"] = True
                    content = {"title": "Центр Хаба", "desc": "Безопасная зона."}

                node = WorldGrid(
                    x=x,
                    y=y,
                    sector_id=sec_id,
                    is_active=is_active,
                    flags=flags,
                    content=content,
                    service_object_key=None,
                )
                grid_batch.append(node)

                # Пишем батчами по 1000, чтобы не забить память
                if len(grid_batch) >= 1000:
                    session.add_all(grid_batch)
                    await session.commit()
                    grid_batch = []
                    log.info(f"   ...processed up to {x}:{y}")

        if grid_batch:
            session.add_all(grid_batch)
            await session.commit()

    log.info("🎉 World Seeding COMPLETED successfully.")


if __name__ == "__main__":
    try:
        asyncio.run(seed_world())
    except RuntimeError:
        log.exception("Seeding failed")
