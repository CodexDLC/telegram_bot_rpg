# scripts/analyze_balance.py
import glob
import os

import pandas as pd

# Настройка отображения Pandas (чтобы таблицы были красивыми)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)

# 1. Пути
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "analytics")
PATTERN = os.path.join(DATA_DIR, "combats_*.csv")

print(f"📂 Читаем данные из: {PATTERN}")

files = glob.glob(PATTERN)
if not files:
    print("❌ Файлов нет.")
    exit()

try:
    df = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
except pd.errors.EmptyDataError:
    print("⚠️ Файл пуст.")
    exit()

print(f"✅ Загружено боев: {len(df)}\n")

# =====================================================
# 1. БАЗОВАЯ СТАТИСТИКА (Винрейт)
# =====================================================
print("🏆 --- ВИНРЕЙТ КОМАНД ---")
if "winner_team" in df.columns:
    print(df["winner_team"].value_counts(normalize=True).mul(100).round(1).astype(str) + "%")
else:
    print("Нет данных.")

# =====================================================
# 2. ДИНАМИКА БОЯ (Длительность)
# =====================================================
print("\n⏱ --- ДИНАМИКА ---")
if "total_rounds" in df.columns:
    avg_rounds = df["total_rounds"].mean()
    print(f"Среднее кол-во раундов: {avg_rounds:.1f}")

    # Проверка на "быстрые смерти" (меньше 5 раундов)
    fast_games = df[df["total_rounds"] < 5]
    print(f"Коротких боев (<5 ходов): {len(fast_games)} ({len(fast_games) / len(df) * 100:.1f}%)")

# =====================================================
# 3. ЭФФЕКТИВНОСТЬ БОЙЦОВ (Урон и защита)
# =====================================================
print("\n⚔️ --- ЭФФЕКТИВНОСТЬ (Средние показатели) ---")

# Мы объединим данные p1 и p2 в одну длинную таблицу, чтобы посчитать среднее "по больнице"
# Берем куски колонок для P1 и переименовываем в общие названия
cols_p1 = ["p1_name", "p1_dmg_dealt", "p1_dmg_taken", "p1_blocks", "p1_dodges", "p1_crits"]
cols_p2 = ["p2_name", "p2_dmg_dealt", "p2_dmg_taken", "p2_blocks", "p2_dodges", "p2_crits"]

# Создаем временные датафреймы
df_p1 = df[cols_p1].rename(columns=lambda x: x.replace("p1_", ""))
df_p2 = df[cols_p2].rename(columns=lambda x: x.replace("p2_", ""))

# Склеиваем их (теперь у нас просто список "Участников")
all_fighters = pd.concat([df_p1, df_p2])

# Группируем по Имени бойца и считаем среднее
# (Если имена одинаковые Gladiator_A - он усреднит все его бои)
if not all_fighters.empty:
    stats = all_fighters.groupby("name").mean().round(1)
    print(stats)
else:
    print("Нет данных об игроках.")
