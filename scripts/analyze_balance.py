import glob

import pandas as pd

# Читаем все файлы
files = glob.glob("data/analytics/combats_*.csv")
df = pd.concat(pd.read_csv(f) for f in files)

print("=== БАЛАНС ОТЧЕТ ===")
print(f"Всего боев: {len(df)}")
print("Винрейт команд:")
print(df["winner_team"].value_counts(normalize=True))
print(f"Средняя длительность: {df['duration'].mean():.1f} сек")
