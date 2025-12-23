import asyncio
import json
import os
import sys
from typing import Any

import pandas as pd
import streamlit as st
from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError

from apps.common.database.repositories import get_monster_repo
from apps.game_core.resources.game_data.items.bases import BASES_DB

# Заменили импорт
from tools.admin_dashboard.ui_core import (
    apply_global_styles,
    get_dashboard_session,
    render_header,
    render_rpg_stat_chart,
)

# --- Адаптация под структуру проекта ---
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

# --- Настройки страницы и логирования ---
apply_global_styles()
render_header(
    "Активные Кланы в Мире", "⚔️", "Просмотр сгенерированных LLM кланов и их участников, которые существуют в БД."
)


# --- Хелперы ---
def get_item_name(item_id: str | None) -> str:
    """Возвращает читаемое имя предмета по его ID."""
    if not item_id:
        return "-"
    for category in BASES_DB.values():
        if item_id in category:
            return f"{category[item_id]['name_ru']} ({item_id})"
    return item_id


# --- Загрузка данных ---
async def load_clans_data():
    """
    Асинхронно загружает все кланы и их участников из базы данных.
    """
    log.info("LoadClans | event=start")
    try:
        async with get_dashboard_session() as session:
            repo = get_monster_repo(session)
            clans = await repo.get_all_clans()
            log.info(f"LoadClans | event=success count={len(clans)}")
            return clans
    except SQLAlchemyError:
        log.exception("LoadClansError | reason=db_error")
        st.error("Ошибка подключения к базе данных.")
        return []


# --- Основная логика ---
async def run_async_app():
    """Запускает асинхронную часть Streamlit приложения."""
    clans = await load_clans_data()

    if not clans:
        st.warning("В базе данных нет сгенерированных кланов.")
        return

    st.info(f"Найдено {len(clans)} кланов.")
    st.divider()

    # Фильтры
    col1, col2 = st.columns(2)
    family_ids = sorted(list(set(c.family_id for c in clans)))
    selected_family = col1.selectbox("Фильтр по семейству:", ["Все"] + family_ids)
    tiers = sorted(list(set(c.tier for c in clans)))
    selected_tier = col2.selectbox("Фильтр по тиру:", ["Все"] + tiers)

    filtered_clans = [
        c
        for c in clans
        if (selected_family == "Все" or c.family_id == selected_family)
        and (selected_tier == "Все" or c.tier == selected_tier)
    ]

    if not filtered_clans:
        st.warning("Нет кланов, соответствующих фильтрам.")
        return

    for clan in filtered_clans:
        with st.expander(f"🏰 {clan.name_ru} (Tier: {clan.tier})"):
            st.markdown("### 🏰 Данные Клана (GeneratedClanORM)")
            c1, c2 = st.columns(2)
            with c1:
                st.info(f"**Название (name_ru):** {clan.name_ru}")
                st.write(f"**Описание (description):** {clan.description}")
                st.caption(f"Family ID: `{clan.family_id}` | Zone ID: `{clan.zone_id}`")

            with c2:
                st.write("**Контекст генерации (raw_tags):**")
                st.code(clan.raw_tags)
                with st.expander("Показать полный JSON (flavor_content)"):
                    st.json(clan.flavor_content)

            st.divider()

            st.markdown(f"### 👹 Участники ({len(clan.members)})")

            if not clan.members:
                st.text("У этого клана нет участников.")
                continue

            monster_records = []
            for m in clan.members:
                encounter_text = "N/A"
                try:
                    flavor = json.loads(m.description)
                    encounter_text = flavor.get("encounter", "N/A")
                except (json.JSONDecodeError, TypeError):
                    log.warning(f"ParseFlavorFail | monster_id={m.id} data='{m.description}'")
                    pass

                monster_records.append(
                    {
                        "ID": str(m.id)[:8] + "...",
                        "Имя (name_ru)": m.name_ru,
                        "Вариант": m.variant_key,
                        "Роль": m.role,
                        "Угроза": m.threat_rating,
                        "Встреча (Encounter)": encounter_text[:50] + "..."
                        if len(encounter_text) > 50
                        else encounter_text,
                    }
                )
            st.dataframe(pd.DataFrame(monster_records), use_container_width=True, hide_index=True)

            monster_map: dict[int, Any] = {m.id: m for m in clan.members}

            def format_monster(x: int, m_map: dict[int, Any] = monster_map) -> str:
                return f"{m_map[x].name_ru} ({m_map[x].variant_key})"

            selected_monster_id = st.selectbox(
                "Выберите монстра для детального просмотра:",
                options=list(monster_map.keys()),
                format_func=format_monster,
                key=f"select_{clan.id}",
            )

            if selected_monster_id:
                monster = monster_map[selected_monster_id]

                try:
                    flavor_texts = json.loads(monster.description)
                except (json.JSONDecodeError, TypeError):
                    flavor_texts = {
                        "appearance": monster.description,
                        "encounter": "N/A",
                        "behavior": "N/A",
                    }

                st.markdown("#### 🔍 Инспектор Монстра")
                m1, m2 = st.columns([2, 3])

                with m1:
                    st.success(f"**{monster.name_ru}**")
                    st.caption(f"ID: `{monster.id}`")
                    st.write(f"**Роль:** {monster.role.capitalize()} | **Угроза:** {monster.threat_rating}")

                    st.markdown("---")
                    st.markdown(f"**⚔️ Встреча (Encounter):** *{flavor_texts.get('encounter', 'N/A')}*")
                    st.markdown(f"**👁️ Внешний вид (Appearance):** *{flavor_texts.get('appearance', 'N/A')}*")
                    st.markdown(f"**🧠 Поведение (Behavior):** *{flavor_texts.get('behavior', 'N/A')}*")
                    st.markdown("---")

                    st.markdown("##### 🎒 Экипировка (loadout_ids)")
                    loadout = monster.loadout_ids
                    if loadout:
                        for slot, item_id in loadout.items():
                            st.write(f"**{slot}:** {get_item_name(item_id)}")
                    else:
                        st.text("Нет экипировки")

                with m2:
                    stats = monster.scaled_base_stats
                    render_rpg_stat_chart(stats, "Характеристики", key=f"chart_{monster.id}")

                    st.markdown("##### ⚔️ Навыки (skills_snapshot)")
                    st.write(", ".join(monster.skills_snapshot))


def main():
    """Основная точка входа для запуска приложения."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_async_app())


if __name__ == "__main__":
    main()
