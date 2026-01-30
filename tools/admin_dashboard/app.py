import asyncio
import os
import sys
import time
from typing import Any

import streamlit as st
from loguru import logger as log
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# --- 1. Настройка путей ---
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from apps.common.core.loguru_setup import setup_loguru  # noqa: E402
from src.backend.services import ScenarioLoader  # noqa: E402

# Заменили импорт
from tools.admin_dashboard.ui_core import apply_global_styles, get_dashboard_session, render_header  # noqa: E402

# --- 2. Инициализация ---
setup_loguru()

st.set_page_config(
    page_title="Admin Dashboard",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_global_styles()


# --- 3. Логика загрузки данных (Real Data) ---
async def load_kpi_data() -> dict[str, Any]:
    """
    Загружает реальные метрики из БД с замером времени отклика.
    Возвращает dict с данными.
    """
    start_time = time.perf_counter()
    stats: dict[str, Any] = {
        "players_total": 0,
        "monster_clans": 0,
        "active_cells": 0,
        "db_latency_ms": 0.0,
        "db_status": False,
    }

    try:
        # Используем get_dashboard_session
        async with get_dashboard_session() as session:
            # 1. Считаем игроков (таблица users)
            res_users = await session.execute(text("SELECT count(*) FROM users"))
            stats["players_total"] = res_users.scalar() or 0

            # 2. Считаем кланы монстров (таблица generated_clans)
            try:
                res_clans = await session.execute(text("SELECT count(*) FROM generated_clans"))
                stats["monster_clans"] = res_clans.scalar() or 0
            except SQLAlchemyError:
                stats["monster_clans"] = 0

            # 3. Считаем активные клетки (world_nodes)
            try:
                res_cells = await session.execute(text("SELECT count(*) FROM world_nodes"))
                stats["active_cells"] = res_cells.scalar() or 0
            except SQLAlchemyError:
                stats["active_cells"] = 0

            # 4. Проверка коннекта (Health Check)
            await session.execute(text("SELECT 1"))
            stats["db_status"] = True

    except SQLAlchemyError as e:
        log.error(f"KPI Fetch Error: {e}")
        stats["db_status"] = False

    end_time = time.perf_counter()
    stats["db_latency_ms"] = round((end_time - start_time) * 1000, 2)

    return stats


async def reload_scenarios_action():
    """
    Перезагружает сценарии из JSON в БД.
    """
    try:
        # Используем get_dashboard_session
        async with get_dashboard_session() as session:
            loader = ScenarioLoader(session)
            await loader.load_all_scenarios()
        return True, "Сценарии успешно обновлены!"
    except Exception as e:  # noqa: BLE001
        log.exception(f"Reload Scenarios Failed: {e}")
        return False, f"Ошибка обновления: {e}"


# --- 4. Основной интерфейс ---

# Заголовок
render_header("COMMAND CENTER", "🛠️", "// System Status & Overview")

# Загрузка данных
with st.spinner("Connecting to neural network..."):
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    kpi = asyncio.run(load_kpi_data())

# --- 5. KPI Панель ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="👥 Игроки (Total)",
        value=kpi["players_total"],
        help="Общее количество зарегистрированных пользователей в таблице users.",
    )

with col2:
    st.metric(
        label="👹 Монстр-Кланы",
        value=kpi["monster_clans"],
        delta="Популяция",
        delta_color="off",
        help="Количество сгенерированных групп монстров (GeneratedClanORM), бродящих по миру.",
    )

with col3:
    st.metric(
        label="🌍 Активные клетки", value=kpi["active_cells"], help="Количество сгенерированных локаций (nodes) в мире."
    )

with col4:
    status_icon = "🟢" if kpi["db_status"] else "🔴"
    st.metric(
        label="🔌 DB Latency",
        value=f"{kpi['db_latency_ms']} ms",
        delta=status_icon,
        help="Время выполнения запроса к БД (ping).",
    )

st.divider()

# --- 6. Quick Actions (Меню быстрых действий) ---
st.subheader("🚀 Quick Actions")
st.caption("Управление состоянием сервера")

with st.container():
    c1, c2, c3 = st.columns(3)

    if c1.button("🔄 Reload Scenarios (JSON -> DB)", use_container_width=True):
        with st.spinner("Обновление сценариев..."):
            success, msg = asyncio.run(reload_scenarios_action())
            if success:
                st.toast(msg, icon="✅")
                st.success(msg)
            else:
                st.toast("Ошибка!", icon="❌")
                st.error(msg)

    if c2.button("🧹 Clear Cache (Redis)", use_container_width=True):
        st.cache_data.clear()
        st.toast("Кэш Streamlit очищен!", icon="🧹")

    if c3.button("📢 Send Global Message", use_container_width=True):
        st.info("Функционал рассылки в разработке.")

# --- 7. Debug Info (скрытый) ---
with st.expander("🔍 Debug: Raw Data"):
    st.json(kpi)
