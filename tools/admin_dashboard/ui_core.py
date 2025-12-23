# apps/admin_dashboard/ui_core.py
from contextlib import asynccontextmanager

import plotly.graph_objects as go
import streamlit as st
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from apps.common.core.settings import settings

# --- CONSTANTS ---
THEME_COLOR = "#E69138"  # Основной акцент (Gold/Orange)
BG_COLOR = "#0E1117"  # Фон страницы
CARD_BG = "#1E1E1E"  # Фон карточек
TEXT_COLOR = "#FAFAFA"
FONT = "'Source Code Pro', monospace"  # Или 'Orbitron' для киберпанка


def apply_global_styles():
    """Применяет глобальный CSS ко всему приложению."""
    st.markdown(
        f"""
        <style>
            /* Импорт шрифтов */
            @import url('https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@400;600;700&display=swap');
            
            html, body, [class*="css"] {{
                font-family: {FONT};
            }}
            
            /* Заголовки */
            h1, h2, h3 {{
                color: {THEME_COLOR} !important;
                text-transform: uppercase;
                letter-spacing: 2px;
            }}
            
            /* Стилизация Expander (сделаем их похожими на квесты) */
            div[data-testid="stExpander"] {{
                background-color: {CARD_BG};
                border: 1px solid #333;
                border-radius: 4px;
            }}
            
            /* Стилизация кнопок */
            div.stButton > button {{
                background-color: #2D2D2D;
                color: {THEME_COLOR};
                border: 1px solid {THEME_COLOR};
                border-radius: 0px; /* Квадратные, брутальные кнопки */
                transition: all 0.3s ease;
            }}
            div.stButton > button:hover {{
                background-color: {THEME_COLOR};
                color: #000;
                box-shadow: 0 0 10px {THEME_COLOR};
            }}
            
            /* Убираем лишние отступы сверху */
            .block-container {{
                padding-top: 2rem;
            }}
            
            /* Кастомные метрики */
            div[data-testid="stMetricValue"] {{
                color: #00FF7F !important; /* Acid Green for numbers */
                font-size: 26px !important;
            }}
        </style>
    """,
        unsafe_allow_html=True,
    )


def render_header(title: str, icon: str, subtitle: str = ""):
    """Единый заголовок для всех страниц."""
    st.markdown(f"# {icon} {title}")
    if subtitle:
        st.caption(f"// {subtitle}")
    st.divider()


def render_rpg_stat_chart(stats: dict, title: str = "Stats", key: str = None):
    """Рисует красивую паутинную диаграмму (Radar Chart) для статов."""
    # Нормализация данных для графика
    categories = list(stats.keys())
    values = list(stats.values())

    # Замыкаем круг графика
    categories = [*categories, categories[0]]
    values = [*values, values[0]]

    fig = go.Figure(
        data=go.Scatterpolar(
            r=values, theta=categories, fill="toself", line_color=THEME_COLOR, fillcolor="rgba(230, 145, 56, 0.2)"
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 30],  # Максимум стата, подстрой под игру
                gridcolor="#333",
                linecolor="#333",
            ),
            bgcolor=CARD_BG,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        margin=dict(l=20, r=20, t=20, b=20),
        height=300,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=key)


def card_container(title: str, context_func):
    """Обертка для контента в виде карточки."""
    with st.container():
        st.markdown(
            f"""
        <div style="background-color: {CARD_BG}; padding: 15px; border-left: 3px solid {THEME_COLOR}; margin-bottom: 10px;">
            <h4 style="margin: 0; padding: 0; color: white;">{title}</h4>
        </div>
        """,
            unsafe_allow_html=True,
        )
        context_func()


def render_inventory_grid(items):
    cols = st.columns(5)  # 5 слотов в ряд
    for i, item in enumerate(items):
        with cols[i % 5]:
            st.markdown(
                f"""
            <div style="border: 1px solid #444; text-align: center; padding: 10px; background: #222;">
                <div style="font-size: 30px;">⚔️</div> <div style="font-size: 12px; color: #aaa;">{item.item_id}</div>
                <div style="font-size: 14px; font-weight: bold;">x{item.quantity}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )


# --- DATABASE SESSION FOR STREAMLIT ---


@asynccontextmanager
async def get_dashboard_session():
    """
    Создает изолированную сессию БД для Streamlit.
    Использует NullPool, чтобы не конфликтовать с event loop при перезагрузках страницы.
    """
    # Создаем движок с NullPool (каждое соединение закрывается сразу)
    engine = create_async_engine(settings.sqlalchemy_database_url, echo=False, poolclass=NullPool)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    # Обязательно закрываем движок, чтобы не висели коннекты
    await engine.dispose()
