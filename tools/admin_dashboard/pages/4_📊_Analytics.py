import glob
import os

import pandas as pd
import plotly.express as px
import streamlit as st

from tools.admin_dashboard.ui_core import apply_global_styles, render_header

# Настройки страницы
apply_global_styles()
render_header("Аналитика", "📊")

# Путь к папке с логами
LOG_DIRECTORY = "data/analytics"


@st.cache_data(ttl=60)
def load_combat_data():
    """Загружает и парсит CSV файлы боев."""
    try:
        csv_files = glob.glob(os.path.join(LOG_DIRECTORY, "combats_*.csv"))
        # Если старые файлы назывались просто *.csv, можно оставить "*.csv",
        # но лучше фильтровать по префиксу, если появятся другие типы логов.
        if not csv_files:
            # Фолбек на все csv, если нет с префиксом combats_
            csv_files = glob.glob(os.path.join(LOG_DIRECTORY, "*.csv"))

        if not csv_files:
            return pd.DataFrame(), []

        df_list = [pd.read_csv(file) for file in csv_files]
        df = pd.concat(df_list, ignore_index=True)

        if "date_iso" in df.columns:
            df["date_iso"] = pd.to_datetime(df["date_iso"])
        return df, csv_files
    except Exception as e:  # noqa: BLE001
        st.error(f"Ошибка чтения файлов боев: {e}")
        return pd.DataFrame(), []


# Создаем вкладки для разных разделов аналитики
tab_combat, tab_economy, tab_world = st.tabs(["⚔️ Боевка", "💰 Экономика", "🌍 Мир"])

# --- ВКЛАДКА: БОЕВКА ---
with tab_combat:
    st.subheader("Анализ боевой системы")

    df, loaded_files = load_combat_data()

    if df.empty:
        st.warning("Нет данных о боях. Убедитесь, что бои проходят и логи записываются в data/analytics.")
    else:
        # --- ИСХОДНЫЕ ФАЙЛЫ ---
        with st.expander(f"Загружено файлов: {len(loaded_files)}"):
            for file in loaded_files:
                st.text(os.path.basename(file))

        # --- ОБЩАЯ СТАТИСТИКА ---
        st.markdown("#### Общие показатели")
        total_fights = len(df)
        avg_duration = df["duration_sec"].mean()
        avg_rounds = df["total_rounds"].mean()

        col1, col2, col3 = st.columns(3)
        col1.metric("Всего боев", total_fights)
        col2.metric("Средняя длит. (сек)", f"{avg_duration:.2f}")
        col3.metric("Среднее кол-во раундов", f"{avg_rounds:.2f}")

        st.divider()

        # --- АНАЛИЗ ПОБЕД ---
        st.markdown("#### Баланс побед")
        winner_counts = df["winner_team"].value_counts().reset_index()
        winner_counts.columns = ["team", "wins"]
        fig = px.bar(winner_counts, x="team", y="wins", title="Победы по командам", color_discrete_sequence=["#E69138"])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # --- АНАЛИЗ УРОНА И ВЫЖИВАЕМОСТИ ---
        st.markdown("#### Эффективность (P1 vs P2)")
        p1_stats = df[["p1_dmg_dealt", "p1_dmg_taken", "p1_healing"]].sum().rename("Player 1")
        p2_stats = df[["p2_dmg_dealt", "p2_dmg_taken", "p2_healing"]].sum().rename("Player 2")

        combat_stats = pd.concat([p1_stats, p2_stats], axis=1)
        st.dataframe(combat_stats, use_container_width=True)

        st.divider()

        # --- ПОСЛЕДНИЕ БОИ ---
        st.markdown("#### Лог последних 10 боев")
        st.dataframe(
            df.sort_values(by="timestamp", ascending=False).head(10),
            use_container_width=True,
            hide_index=True,
        )

# --- ВКЛАДКА: ЭКОНОМИКА ---
with tab_economy:
    st.header("Экономическая аналитика")
    st.info("Здесь будут графики по золоту, торговле и ресурсам.")
    # В будущем здесь будет load_economy_data()

# --- ВКЛАДКА: МИР ---
with tab_world:
    st.header("Аналитика мира")
    st.info("Здесь будет тепловая карта перемещений игроков и статистика по зонам.")
