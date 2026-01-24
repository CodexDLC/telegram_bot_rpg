import os
import sys

import pandas as pd
import streamlit as st

from backend.resources.game_data import ALL_FAMILIES_RAW
from tools.admin_dashboard.ui_core import apply_global_styles, render_header, render_rpg_stat_chart

# --- Адаптация под структуру проекта ---
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

# --- Настройки страницы ---
apply_global_styles()
render_header("Бестиарий", "👹", "Database: Connected")


# --- Подготовка данных ---
@st.cache_data
def get_monster_dataframe():
    """Преобразует список семейств в удобный для фильтрации DataFrame."""
    records = []
    for family in ALL_FAMILIES_RAW:
        if not isinstance(family, dict):
            continue

        family_id = family.get("id", "N/A")
        archetype = family.get("archetype", "N/A")

        variants = family.get("variants")
        if not isinstance(variants, dict):
            continue

        for variant_id, data in variants.items():
            if not isinstance(data, dict):
                continue

            stats = data.get("base_stats", {})
            if not isinstance(stats, dict):
                stats = {}

            records.append(
                {
                    "family_id": family_id,
                    "archetype": archetype,
                    "variant_id": variant_id,
                    "role": data.get("role", "-"),
                    "cost": data.get("cost", 0),
                    "min_tier": data.get("min_tier", 0),
                    "max_tier": data.get("max_tier", 7),
                    "strength": stats.get("strength", 0),
                    "agility": stats.get("agility", 0),
                    "endurance": stats.get("endurance", 0),
                    "intelligence": stats.get("intelligence", 0),
                    "wisdom": stats.get("wisdom", 0),
                    "men": stats.get("men", 0),
                    "perception": stats.get("perception", 0),
                    "charisma": stats.get("charisma", 0),
                    "luck": stats.get("luck", 0),
                }
            )
    return pd.DataFrame(records)


df = get_monster_dataframe()

# --- Фильтры в сайдбаре ---
with st.sidebar:
    st.header("Фильтры")

    archetypes = ["Все"] + sorted(df["archetype"].unique())
    selected_archetype = st.selectbox("Архетип", archetypes)

    selected_tier = st.slider("Уровень угрозы (Tier)", 0, 7, (0, 7))

# --- Фильтрация данных ---
filtered_df = df.copy()
if selected_archetype != "Все":
    filtered_df = filtered_df[filtered_df["archetype"] == selected_archetype]

filtered_df = filtered_df[(filtered_df["min_tier"] <= selected_tier[1]) & (filtered_df["max_tier"] >= selected_tier[0])]

# --- Отображение семейств ---
if filtered_df.empty:
    st.warning("Не найдено монстров, соответствующих фильтрам.")
else:
    families_to_show = filtered_df["family_id"].unique()

    for family_id in sorted(families_to_show):
        family_data = filtered_df[filtered_df["family_id"] == family_id]
        family_archetype = family_data["archetype"].iloc[0]

        with st.expander(f"👹 {family_id.replace('_', ' ').title()} ({family_archetype})"):
            st.markdown("##### Варианты монстров")

            display_columns = [
                "variant_id",
                "role",
                "cost",
                "min_tier",
                "max_tier",
                "strength",
                "agility",
                "endurance",
                "intelligence",
                "wisdom",
                "men",
                "perception",
                "charisma",
                "luck",
            ]
            st.dataframe(family_data[display_columns].sort_values(by="cost"), use_container_width=True, hide_index=True)

            st.markdown("---")
            selected_variant = st.selectbox(
                "Выберите юнита для детального просмотра:",
                options=[""] + list(family_data["variant_id"]),
                key=f"select_{family_id}",
            )

            if selected_variant:
                variant_details = family_data[family_data["variant_id"] == selected_variant].iloc[0]

                st.subheader(f"🔍 {variant_details['variant_id']}")

                c1, c2 = st.columns([1, 1])
                with c1:
                    st.write("Описание и лор...")
                    cols = st.columns(4)
                    cols[0].metric("Cost", variant_details["cost"])
                    cols[1].metric("Min Tier", variant_details["min_tier"])
                    cols[2].metric("Max Tier", variant_details["max_tier"])
                    cols[3].metric("Role", variant_details["role"].capitalize())

                with c2:
                    stats_dict = {
                        "STR": variant_details["strength"],
                        "AGI": variant_details["agility"],
                        "INT": variant_details["intelligence"],
                        "LUCK": variant_details["luck"],
                        "END": variant_details["endurance"],
                        "WIS": variant_details["wisdom"],
                        "MEN": variant_details["men"],
                        "PER": variant_details["perception"],
                        "CHA": variant_details["charisma"],
                    }
                    render_rpg_stat_chart(stats_dict, f"Stats: {variant_details['variant_id']}")
