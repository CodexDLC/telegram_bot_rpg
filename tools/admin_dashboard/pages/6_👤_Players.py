import asyncio
import os
import sys
from typing import Any

import streamlit as st
from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError

from apps.bot.resources.status_menu.modifer_group_data import MODIFIER_HIERARCHY
from apps.bot.resources.status_menu.skill_group_data import SKILL_HIERARCHY
from apps.common.database.repositories import (
    get_inventory_repo,
    get_skill_progress_repo,
    get_symbiote_repo,
    get_user_repo,
    get_wallet_repo,
)
from apps.game_core.game_service.status.stats_aggregation_service import StatsAggregationService

# Заменили импорт
from tools.admin_dashboard.ui_core import (
    apply_global_styles,
    get_dashboard_session,
    render_header,
    render_inventory_grid,
    render_rpg_stat_chart,
)

# --- Настройка путей ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Константы ---
ITEMS_PER_PAGE = 10
PAGE_TITLE = "👤 Admin Panel: Players"
PAGE_ICON = "⚔️"

apply_global_styles()

# --- CSS STYLING ---
st.markdown(
    """
<style>
    .stat-card {
        background: linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%);
        border-left: 3px solid #E69138;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .stat-header {
        font-size: 14px;
        color: #E69138;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .stat-value {
        font-size: 24px;
        font-weight: bold;
        color: #00FF7F;
        margin-bottom: 8px;
    }
    .stat-source {
        font-size: 12px;
        color: #AAA;
        margin-left: 10px;
        padding: 3px 0;
        border-left: 2px solid #444;
        padding-left: 10px;
    }
    .skill-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #E69138;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .skill-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .skill-title {
        font-size: 16px;
        font-weight: bold;
        color: #FFD700;
    }
    .skill-rank {
        font-size: 12px;
        color: #AAA;
        background: #333;
        padding: 4px 8px;
        border-radius: 4px;
    }
    .progress-container {
        background: #222;
        border-radius: 4px;
        height: 20px;
        margin: 10px 0;
        overflow: hidden;
        position: relative;
    }
    .progress-bar {
        background: linear-gradient(90deg, #E69138 0%, #FFB84D 100%);
        height: 100%;
        transition: width 0.3s ease;
    }
    .progress-text {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 11px;
        font-weight: bold;
        color: white;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
    }
    .modifier-group {
        background: #1a1a1a;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 4px solid #E69138;
    }
    .modifier-group-title {
        font-size: 18px;
        font-weight: bold;
        color: #E69138;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
</style>
""",
    unsafe_allow_html=True,
)


# --- Хелперы ---
def init_session_state():
    if "selected_user_id" not in st.session_state:
        st.session_state.selected_user_id = None
    if "selected_char_id" not in st.session_state:
        st.session_state.selected_char_id = None
    if "user_page" not in st.session_state:
        st.session_state.user_page = 0


def get_modifier_metadata(key: str) -> tuple[str, str]:
    """Возвращает название и иконку для модификатора из MODIFIER_HIERARCHY."""
    data = MODIFIER_HIERARCHY.get(key, {})
    title = data.get("title", key.replace("_", " ").title())

    # Находим родительскую группу для получения иконки
    icon = "📊"
    for _group_key, group_data in MODIFIER_HIERARCHY.items():
        if "items" in group_data and isinstance(group_data["items"], dict) and key in group_data["items"]:
            icon = group_data.get("title", "").split()[0]  # Берём первый эмодзи
            break

    return title, icon


def get_skill_metadata(skill_key: str) -> dict:
    """Возвращает метаданные о скилле из SKILL_HIERARCHY."""
    data = SKILL_HIERARCHY.get(skill_key, {})
    return {
        "title": data.get("title", skill_key),
        "description": data.get("description", ""),
        "milestones": data.get("items", {}),
    }


def calculate_skill_rank(total_xp: int, milestones: dict) -> tuple[str, int, int, float]:
    """
    Вычисляет текущее звание, прогресс до следующего и процент.

    Returns:
        (current_rank, current_milestone, next_milestone, percentage)
    """
    if not milestones:
        return "🌱 Новичок", 0, 100, 0.0

    sorted_milestones = sorted(milestones.keys())
    current_rank = "🌱 Новичок"
    current_milestone = 0
    next_milestone = sorted_milestones[0] if sorted_milestones else 100

    for threshold in sorted_milestones:
        if total_xp >= threshold:
            current_rank = milestones[threshold]
            current_milestone = threshold
        else:
            next_milestone = threshold
            break
    else:
        next_milestone = sorted_milestones[-1]

    if current_milestone == next_milestone:
        percentage = 100.0
    else:
        xp_in_range = total_xp - current_milestone
        range_size = next_milestone - current_milestone
        percentage = (xp_in_range / range_size * 100) if range_size > 0 else 0.0

    return current_rank, current_milestone, next_milestone, percentage


def orm_to_dict(orm_obj: Any) -> dict[str, Any]:
    if not orm_obj:
        return {}
    if hasattr(orm_obj, "model_dump"):
        return orm_obj.model_dump()
    data = {}
    for key, value in orm_obj.__dict__.items():
        if not key.startswith("_"):
            data[key] = value
    return data


# --- Data Layer ---
async def fetch_users_page(offset: int, limit: int):
    try:
        async with get_dashboard_session() as session:
            repo = get_user_repo(session)
            return await repo.get_users_with_pagination(offset, limit)
    except SQLAlchemyError:
        return [], 0


async def fetch_character_full_details(char_id: int) -> dict[str, Any] | None:
    try:
        async with get_dashboard_session() as session:
            agg_service = StatsAggregationService(session)
            inventory_repo = get_inventory_repo(session)
            skill_repo = get_skill_progress_repo(session)
            wallet_repo = get_wallet_repo(session)
            symbiote_repo = get_symbiote_repo(session)

            return {
                "total_stats": await agg_service.get_character_total_stats(char_id),
                "inventory": await inventory_repo.get_all_items(char_id),
                "skills": await skill_repo.get_all_skills_progress(char_id),
                "wallet": await wallet_repo.get_wallet(char_id),
                "symbiote": await symbiote_repo.get_symbiote(char_id),
            }
    except SQLAlchemyError as e:
        log.error(f"Error: {e}")
        return None


# --- UI Renderers ---


def render_stat_with_sources(stat_name: str, stat_data: dict):
    """Рендерит стат с детальным разбором источников."""
    title, icon = get_modifier_metadata(stat_name)
    total = stat_data.get("total", 0)
    sources = stat_data.get("sources", {})

    st.markdown(
        f"""
    <div class="stat-card">
        <div class="stat-header">{icon} {title}</div>
        <div class="stat-value">{total:,.2f}</div>
    """,
        unsafe_allow_html=True,
    )

    if sources:
        for source_name, value in sources.items():
            sign = "+" if value >= 0 else ""
            st.markdown(f'<div class="stat-source">├─ {source_name}: {sign}{value:,.2f}</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_modifiers_section_grouped(modifiers_data: dict):
    """Рендерит модификаторы, сгруппированные по категориям."""
    if not modifiers_data:
        st.info("Нет активных модификаторов")
        return

    # Получаем группы из MODIFIER_HIERARCHY
    stats_meta = MODIFIER_HIERARCHY.get("stats", {})
    groups = stats_meta.get("items", {})

    for group_key, group_title in groups.items():
        group_meta = MODIFIER_HIERARCHY.get(group_key, {})
        group_mods = group_meta.get("items", {})

        if not group_mods:
            continue

        # Фильтруем модификаторы, которые есть в этой группе
        relevant_mods = {k: v for k, v in modifiers_data.items() if k in group_mods}

        if not relevant_mods:
            continue

        with st.expander(f"{group_title}", expanded=False):
            cols = st.columns(2)
            for idx, (mod_key, mod_data) in enumerate(relevant_mods.items()):
                with cols[idx % 2]:
                    render_stat_with_sources(mod_key, mod_data)


def render_stats_section_grouped(stats_data: dict):
    """Рендерит базовые характеристики с группировкой и радар-чартом."""
    if not stats_data:
        st.warning("Нет данных")
        return

    # Подготовка данных для графика
    key_map = {
        "strength": "STR",
        "agility": "AGI",
        "endurance": "END",
        "intelligence": "INT",
        "wisdom": "WIS",
        "men": "MEN",
        "perception": "PER",
        "charisma": "CHA",
        "luck": "LUCK",
    }

    chart_data = {}
    for k, v in stats_data.items():
        if k in key_map:
            chart_data[key_map[k]] = v["total"]

    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown("#### 🕸️ Radar Chart")
        render_rpg_stat_chart(chart_data, "Player Stats", key="player_stats_chart")

    with c2:
        st.markdown("#### 📊 Детализация")
        base_stats = [
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

        for stat_key in base_stats:
            if stat_key in stats_data:
                render_stat_with_sources(stat_key, stats_data[stat_key])


def render_skills_section_modern(skills_data: list):
    """Рендерит скиллы с красивыми прогресс-барами и группировкой."""
    if not skills_data:
        st.info("Нет разблокированных навыков")
        return

    # Группируем скиллы по категориям
    skills_meta = SKILL_HIERARCHY.get("skills", {})
    skill_groups = skills_meta.get("items", {})

    # Создаём словарь skill_key -> group_key
    skill_to_group = {}
    for group_key, group_title in skill_groups.items():
        group_meta = SKILL_HIERARCHY.get(group_key, {})
        group_skills = group_meta.get("items", {})
        for skill_key in group_skills:
            skill_to_group[skill_key] = (group_key, group_title)

    # Группируем скиллы игрока
    grouped_skills: dict[str, list[dict[str, Any]]] = {}
    for skill in skills_data:
        skill_dict = skill.model_dump() if hasattr(skill, "model_dump") else skill
        skill_key = skill_dict.get("skill_key")

        if skill_key and skill_key in skill_to_group:
            group_key, group_title = skill_to_group[skill_key]
            if group_key not in grouped_skills:
                grouped_skills[group_key] = []
            grouped_skills[group_key].append(skill_dict)

    # Рендерим по группам
    for group_key, group_skills_list in grouped_skills.items():
        group_meta = SKILL_HIERARCHY.get(group_key, {})
        group_title = group_meta.get("title", group_key)

        with st.expander(f"{group_title} ({len(group_skills_list)})", expanded=True):
            for skill_dict in group_skills_list:
                render_single_skill_card(skill_dict)


def render_single_skill_card(skill_dict: dict):
    """Рендерит одну карточку навыка с прогресс-баром."""
    skill_key = skill_dict.get("skill_key")
    if not skill_key:
        return

    total_xp = skill_dict.get("total_xp", 0)
    is_unlocked = skill_dict.get("is_unlocked", False)
    progress_state = skill_dict.get("progress_state", "PAUSE")

    metadata = get_skill_metadata(skill_key)
    title = metadata["title"]
    milestones = metadata["milestones"]

    current_rank, current_milestone, next_milestone, percentage = calculate_skill_rank(total_xp, milestones)

    # Статус
    status_icons = {
        "PLUS": "📈",
        "MINUS": "📉",
        "PAUSE": "⏸️",
    }
    status_icon = status_icons.get(str(progress_state), "⏸️")

    lock_icon = "🔓" if is_unlocked else "🔒"

    st.markdown(
        f"""
    <div class="skill-card">
        <div class="skill-header">
            <div class="skill-title">{lock_icon} {title}</div>
            <div class="skill-rank">{status_icon} {current_rank}</div>
        </div>
        <div class="progress-container">
            <div class="progress-bar" style="width: {percentage}%"></div>
            <div class="progress-text">{percentage:.1f}% • {total_xp:,} / {next_milestone:,} XP</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_inventory_section(inventory: list):
    """Секция инвентаря таблицей."""
    if not inventory:
        st.info("🎒 Инвентарь пуст")
        return
    render_inventory_grid(inventory)


def render_wallet_section(wallet_obj: Any):
    """Секция кошелька с разбивкой по типам валют."""
    if not wallet_obj:
        st.warning("Кошелек не найден")
        return

    w_data = orm_to_dict(wallet_obj)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown('<div class="modifier-group-title">💰 Валюта</div>', unsafe_allow_html=True)
        curr = w_data.get("currency", {})
        if curr:
            for k, v in curr.items():
                st.info(f"**{k.title()}**: {v:,}")
        else:
            st.caption("Пусто")

    with c2:
        st.markdown('<div class="modifier-group-title">🔩 Компоненты</div>', unsafe_allow_html=True)
        comp = w_data.get("components", {})
        if comp:
            for k, v in comp.items():
                st.write(f"**{k}**: {v:,}")
        else:
            st.caption("Пусто")

    with c3:
        st.markdown('<div class="modifier-group-title">💎 Ресурсы</div>', unsafe_allow_html=True)
        res = w_data.get("resources", {})
        if res:
            for k, v in res.items():
                st.write(f"**{k}**: {v:,}")
        else:
            st.caption("Пусто")


def render_symbiote_section(symbiote_obj: Any):
    if not symbiote_obj:
        st.info("Нет симбиота")
        return

    s_data = orm_to_dict(symbiote_obj)

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f"### 🦠 {s_data.get('symbiote_name', 'Unknown')}")
        st.metric("Rank", s_data.get("gift_rank", 0))
        st.metric("XP", s_data.get("gift_xp", 0))
    with c2:
        st.json(s_data)


def render_character_view(char_id: int):
    """Главный экран просмотра персонажа с аккордеоном."""
    if st.button("⬅️ Вернуться к списку", type="primary"):
        st.session_state.selected_user_id = None
        st.session_state.selected_char_id = None
        st.rerun()

    # Загрузка
    with st.spinner("Загрузка досье персонажа..."):
        details = asyncio.run(fetch_character_full_details(char_id))

    if not details:
        st.error("Ошибка получения данных.")
        return

    render_header(f"🕵️ Досье Персонажа #{char_id}", "👤")

    # --- СЕКЦИИ (Expanders) ---

    with st.expander("📊 1. БАЗОВЫЕ ХАРАКТЕРИСТИКИ (Stats)", expanded=True):
        render_stats_section_grouped(details.get("total_stats", {}).get("stats", {}))

    with st.expander("⚡ 2. МОДИФИКАТОРЫ (Modifiers)", expanded=False):
        render_modifiers_section_grouped(details.get("total_stats", {}).get("modifiers", {}))

    with st.expander("📚 3. НАВЫКИ (Skills)", expanded=False):
        render_skills_section_modern(details.get("skills", []))

    with st.expander("🎒 4. ИНВЕНТАРЬ (Inventory)", expanded=False):
        render_inventory_section(details.get("inventory", []))

    with st.expander("💰 5. КОШЕЛЕК (Wallet)", expanded=False):
        render_wallet_section(details.get("wallet"))

    with st.expander("🦠 6. СИМБИОТ (Symbiote)", expanded=False):
        render_symbiote_section(details.get("symbiote"))


def render_users_list_view():
    render_header("👥 Список Игроков", "👤")

    offset = st.session_state.user_page * ITEMS_PER_PAGE
    users, total = asyncio.run(fetch_users_page(offset, ITEMS_PER_PAGE))

    # Pagination Logic
    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    curr = st.session_state.user_page + 1

    c1, c2, c3 = st.columns([1, 4, 1])
    with c1:
        if st.session_state.user_page > 0 and st.button("⬅️ Назад"):
            st.session_state.user_page -= 1
            st.rerun()
    with c2:
        st.markdown(f"<div style='text-align:center'>Страница {curr} / {total_pages}</div>", unsafe_allow_html=True)
    with c3:
        if curr < total_pages and st.button("Вперед ➡️"):
            st.session_state.user_page += 1
            st.rerun()

    st.divider()

    for user in users:
        with st.container(border=True):
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown(f"### {user.username or 'NoName'}")
                st.caption(f"ID: {user.telegram_id} | Reg: {user.created_at.strftime('%Y-%m-%d')}")
            with cols[1]:
                if user.characters:
                    for char in user.characters:
                        if st.button(f"Открыть: {char.name}", key=f"btn_{char.character_id}"):
                            st.session_state.selected_user_id = user.telegram_id
                            st.session_state.selected_char_id = char.character_id
                            st.rerun()
                else:
                    st.write("Нет персонажей")


# --- MAIN ---
def main():
    init_session_state()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    if st.session_state.selected_char_id:
        render_character_view(st.session_state.selected_char_id)
    else:
        render_users_list_view()


if __name__ == "__main__":
    main()
