import asyncio
import os
import sys
from typing import cast

import streamlit as st
from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError

from src.backend.database.postgres.repositories import get_monster_repo, get_world_repo

# Заменили импорт
from tools.admin_dashboard.ui_core import apply_global_styles, get_dashboard_session, render_header

# --- Адаптация под структуру проекта ---
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

# --- Настройки страницы и логирования ---
apply_global_styles()

# --- Состояние сессии ---
if "selected_region" not in st.session_state:
    st.session_state.selected_region = None
if "selected_zone" not in st.session_state:
    st.session_state.selected_zone = None
if "selected_cell" not in st.session_state:
    st.session_state.selected_cell = None

# --- Иконки ---
BIOME_ICONS = {
    "city_ruins": "🏙️",
    "forest": "🌲",
    "swamp": "🐊",
    "mountains": "🏔️",
    "wasteland": "☢️",
    "meadow": "🌼",
    "hills": "⛰️",
    "canyon": "🏜️",
    "grassland": "🌾",
    "savanna": "🦁",
    "jungle": "🌴",
    "marsh": "🐸",
    "badlands": "🌋",
    "highlands": "🦅",
    "default": "❓",
}

TERRAIN_ICONS = {
    "road": "🛣️",
    "path": "👣",
    "wall": "🧱",
    "gate": "🚪",
    "forest": "🌲",
    "water": "💧",
    "mountain": "⛰️",
    "monolithic_wall": "⬛",
    "city_gate_outer": "⛩️",
    "ruin_road_main": "🛣️",
    "static_structure": "🏰",
    "wall_breach": "🏚️",
}


def get_terrain_icon(terrain_key: str, biome_id: str, has_road: bool) -> str:
    """Определяет иконку для клетки на основе ее типа и биома."""
    base_icon = BIOME_ICONS.get(biome_id, BIOME_ICONS["default"])

    for key, icon in TERRAIN_ICONS.items():
        if key in terrain_key and key not in ["road", "path", "ruin_road_main"]:
            return icon

    if has_road:
        return f"{base_icon}🛣️"

    terrain_icon = "⬜"
    for key, icon in TERRAIN_ICONS.items():
        if key in terrain_key:
            terrain_icon = icon
            break

    if terrain_icon == base_icon:
        return base_icon

    if terrain_icon != "⬜":
        return terrain_icon

    return base_icon


# --- Загрузка данных ---
async def load_region_list() -> list[str]:
    """Загружает список всех существующих ID регионов."""
    log.info("LoadRegions | event=start")
    try:
        async with get_dashboard_session() as session:
            repo = get_world_repo(session)
            regions = await repo.get_all_regions()
            region_ids = [r.id for r in regions]
            log.info(f"LoadRegions | event=success count={len(region_ids)}")
            return region_ids
    except SQLAlchemyError:
        log.exception("LoadRegionsError | reason=db_error")
        st.error("Ошибка загрузки списка регионов.")
        return []


async def load_zone_data(region_id: str) -> list:
    """Загружает данные о зонах для указанного региона."""
    log.info(f"LoadZones | event=start region_id='{region_id}'")
    try:
        async with get_dashboard_session() as session:
            repo = get_world_repo(session)
            zones = await repo.get_zones_by_region(region_id)
            log.info(f"LoadZones | event=success region_id='{region_id}' count={len(zones)}")
            return [(z.id, z.biome_id) for z in zones]
    except SQLAlchemyError:
        log.exception(f"LoadZonesError | reason=db_error region_id='{region_id}'")
        st.error(f"Ошибка загрузки зон для региона {region_id}.")
        return []


async def load_cells_and_clans_data(zone_id: str) -> tuple[list, str, list]:
    """Загружает клетки и кланы для указанной зоны."""
    log.info(f"LoadCellsAndClans | event=start zone_id='{zone_id}'")
    try:
        async with get_dashboard_session() as session:
            world_repo = get_world_repo(session)
            monster_repo = get_monster_repo(session)

            zone = await world_repo.get_zone(zone_id)
            zone_biome = zone.biome_id if zone else "default"

            cells = await world_repo.get_nodes_by_zone(zone_id)
            clans = await monster_repo.get_clans_by_zone(zone_id)

            log.info(f"LoadCellsAndClans | event=success zone_id='{zone_id}' cells={len(cells)} clans={len(clans)}")
            return cells, zone_biome, clans
    except SQLAlchemyError:
        log.exception(f"LoadCellsAndClansError | reason=db_error zone_id='{zone_id}'")
        st.error(f"Ошибка загрузки данных для зоны {zone_id}.")
        return [], "error", []


# --- Рендеринг ---
def render_regions_grid(existing_regions: list[str]):
    """Отображает сетку регионов."""
    render_header("Карта Мира (Регионы)", "🌍", "Выберите регион для просмотра зон.")

    region_rows = ["A", "B", "C", "D", "E", "F", "G"]
    existing_set = set(existing_regions)

    with st.container():
        for row_char in region_rows:
            cols = st.columns(7)
            for j, col in enumerate(cols):
                region_id = f"{row_char}{j + 1}"
                if region_id in existing_set:
                    if col.button(f"📍 {region_id}", key=f"btn_{region_id}", use_container_width=True):
                        st.session_state.selected_region = region_id
                        st.rerun()
                else:
                    col.button(f"{region_id}", disabled=True, key=f"empty_{region_id}")


def render_zones_grid(region_id: str, zones_data: list):
    """Отображает сетку зон внутри региона."""
    render_header(f"Регион {region_id}", "📍")
    if st.button("⬅️ Назад к регионам"):
        st.session_state.selected_region = None
        st.rerun()
    st.divider()

    zone_map = {}
    for z_id, biome in zones_data:
        parts = z_id.split("_")
        if len(parts) >= 3:
            zx, zy = int(parts[1]), int(parts[2])
            zone_map[(zx, zy)] = (z_id, biome)

    for zy in range(3):
        cols = st.columns(3)
        for zx, col in enumerate(cols):
            zone_info = zone_map.get((zx, zy))
            if zone_info:
                z_id, biome = zone_info
                icon = BIOME_ICONS.get(biome, BIOME_ICONS["default"])
                if col.button(f"{icon} {z_id}\n\n{biome}", key=f"btn_zone_{z_id}", use_container_width=True):
                    st.session_state.selected_zone = z_id
                    st.rerun()
            else:
                col.button("❌ Пусто", disabled=True, key=f"empty_{zx}_{zy}")


def render_zone_details(zone_id: str, cells_data: list, zone_biome: str, clans_data: list):
    """Отображает детали зоны: карту клеток и список кланов."""
    render_header(f"Зона {zone_id}", "🏙️", f"Биом: {zone_biome} {BIOME_ICONS.get(zone_biome, '')}")
    if st.button("⬅️ Назад к зонам"):
        st.session_state.selected_zone = None
        st.session_state.selected_cell = None
        st.rerun()

    tab1, tab2 = st.tabs(["Карта Клеток", f"⚔️ Кланы ({len(clans_data)})"])

    with tab1:
        render_cells_grid(zone_id, cells_data, zone_biome)

    with tab2:
        render_clans_list(clans_data)


def render_cells_grid(zone_id: str, cells_data: list, zone_biome: str):
    """Отображает сетку клеток и инспектор для выбранной клетки."""
    if not cells_data:
        st.warning("В этой зоне нет сгенерированных клеток.")
        return

    min_x = min(c.x for c in cells_data)
    min_y = min(c.y for c in cells_data)
    cell_map = {(c.x, c.y): c for c in cells_data}

    for dy in range(5):
        cols = st.columns(5)
        for dx, col in enumerate(cols):
            abs_x, abs_y = min_x + dx, min_y + dy
            cell = cell_map.get((abs_x, abs_y))

            if cell:
                flags = cell.flags if isinstance(cell.flags, dict) else {}
                has_road = flags.get("has_road", False)

                icon = get_terrain_icon(cell.terrain_type, zone_biome, has_road)
                status_icon = "🔥" if cell.is_active else "💤"

                label = f"{icon} {abs_x},{abs_y}\n{status_icon}"
                is_selected = st.session_state.selected_cell == (abs_x, abs_y)
                btn_type = "primary" if is_selected else "secondary"

                if col.button(
                    label,
                    key=f"cell_{abs_x}_{abs_y}",
                    type=cast("Literal['primary', 'secondary', 'tertiary']", btn_type),
                    use_container_width=True,
                ):
                    st.session_state.selected_cell = (abs_x, abs_y)
                    st.rerun()
            else:
                col.button("Empty", disabled=True, key=f"void_{dx}_{dy}")

    if st.session_state.selected_cell:
        cx, cy = st.session_state.selected_cell
        cell_data = cell_map.get((cx, cy))
        if cell_data:
            st.divider()
            st.header(f"🔍 Инспектор Клетки ({cx}, {cy})")
            c1, c2, c3 = st.columns(3)
            c1.info(f"**Terrain:** {cell_data.terrain_type}")
            c2.success(f"**Active:** {bool(cell_data.is_active)}")
            c3.warning(f"**Zone:** {zone_id}")

            with st.expander("🚩 Flags", expanded=True):
                st.json(cell_data.flags)
            with st.expander("📝 Content", expanded=True):
                st.json(cell_data.content)


def render_clans_list(clans_data: list):
    """Отображает список кланов в зоне."""
    if not clans_data:
        st.info("В этой зоне нет зарегистрированных кланов.")
        return

    for clan in clans_data:
        exp_title = f"**{clan.name_ru}** (Тир: {clan.tier}, Семейство: {clan.family_id})"
        with st.expander(exp_title):
            st.markdown(f"**Описание:** *{clan.description}*")
            st.code(f"ID: {clan.id}\nUnique Hash: {clan.unique_hash}", language="bash")
            with st.expander("JSON-детали"):
                st.json({"flavor": clan.flavor_content, "tags": clan.raw_tags})


# 1. Создаем одну асинхронную функцию для всей логики страницы
async def run_async_app():
    if st.session_state.selected_region is None:
        regions = await load_region_list()
        render_regions_grid(regions)
    elif st.session_state.selected_zone is None:
        zones = await load_zone_data(st.session_state.selected_region)
        render_zones_grid(st.session_state.selected_region, zones)
    else:
        # Важно: await здесь заменяет loop.run_until_complete
        cells, zone_biome, clans = await load_cells_and_clans_data(st.session_state.selected_zone)
        render_zone_details(st.session_state.selected_zone, cells, zone_biome, clans)


# 2. Основная точка входа
def main():
    """Основная точка входа для запуска приложения."""
    # ОБЯЗАТЕЛЬНО для Windows и asyncpg
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Запускаем всё приложение в одном чистом цикле событий
    asyncio.run(run_async_app())


if __name__ == "__main__":
    main()
