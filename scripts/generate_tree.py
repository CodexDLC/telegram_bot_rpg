import os
import argparse
import sys

# Конфигурация игнорирования
IGNORE_DIRS = {
    ".git", "venv", ".venv", "__pycache__", ".idea", ".vscode",
    "data", "logs", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".gemini", "build", "dist"
}
IGNORE_EXTENSIONS = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".db", ".sqlite3", ".log"}

def get_project_root():
    """Определяет корень проекта (родитель папки scripts)."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(current_dir)

def get_top_level_dirs(root_path):
    """Возвращает список папок верхнего уровня."""
    try:
        items = os.listdir(root_path)
        dirs = [
            d for d in items 
            if os.path.isdir(os.path.join(root_path, d)) and d not in IGNORE_DIRS
        ]
        return sorted(dirs)
    except OSError as e:
        print(f"Ошибка при чтении директории: {e}")
        return []

def generate_tree(root_path, target_rel_path=None, output_file="project_structure.txt"):
    """
    Генерирует дерево.
    :param root_path: Абсолютный путь к корню проекта.
    :param target_rel_path: Относительный путь к целевой папке (None = весь проект).
    """
    start_path = os.path.join(root_path, target_rel_path) if target_rel_path else root_path
    
    if not os.path.exists(start_path):
        print(f"❌ Путь не найден: {start_path}")
        return

    output_path = os.path.join(root_path, output_file)
    
    print(f"⏳ Генерация дерева для: {target_rel_path or 'ROOT'} -> {output_file} ...")

    with open(output_path, "w", encoding="utf-8") as f:
        header = f"Project Structure: {os.path.basename(root_path)}"
        if target_rel_path:
            header += f"/{target_rel_path}"
        f.write(f"{header}\n\n")

        # Если сканируем подпапку, нужно правильно рассчитать отступы
        # Мы хотим видеть путь от корня? Или только поддерево?
        # Обычно удобнее видеть поддерево.
        
        for root, dirs, files in os.walk(start_path, topdown=True):
            # Фильтрация папок
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            # Расчет уровня вложенности относительно start_path
            rel_path = os.path.relpath(root, start_path)
            if rel_path == ".":
                level = 0
                display_name = os.path.basename(start_path)
            else:
                level = rel_path.count(os.sep) + 1
                display_name = os.path.basename(root)

            indent = "    " * level
            f.write(f"{indent}📂 {display_name}/\n")

            sub_indent = "    " * (level + 1)
            for file in sorted(files):
                if not any(file.endswith(ext) for ext in IGNORE_EXTENSIONS):
                    f.write(f"{sub_indent}📄 {file}\n")

    print(f"✅ Готово! Файл сохранен: {output_path}")

def interactive_mode(root_path):
    """Интерактивное меню выбора."""
    dirs = get_top_level_dirs(root_path)
    
    if not dirs:
        print("⚠️ Нет доступных папок для сканирования.")
        generate_tree(root_path)
        return

    print("\n🔍 Выберите область сканирования:")
    print("0. [ВЕСЬ ПРОЕКТ]")
    
    for i, d in enumerate(dirs, 1):
        print(f"{i}. {d}")

    while True:
        try:
            choice = input("\nВведите номер (или 'q' для выхода): ").strip().lower()
            if choice == 'q':
                sys.exit(0)
            
            idx = int(choice)
            if idx == 0:
                generate_tree(root_path)
                break
            elif 1 <= idx <= len(dirs):
                target = dirs[idx - 1]
                generate_tree(root_path, target)
                break
            else:
                print("❌ Неверный номер.")
        except ValueError:
            print("❌ Введите число.")

def main():
    parser = argparse.ArgumentParser(description="Генератор структуры проекта.")
    parser.add_argument("--all", action="store_true", help="Сгенерировать дерево для всего проекта без вопросов.")
    parser.add_argument("path", nargs="?", help="Относительный путь к папке для сканирования.")
    
    args = parser.parse_args()
    root_path = get_project_root()

    if args.all:
        generate_tree(root_path)
    elif args.path:
        generate_tree(root_path, args.path)
    else:
        interactive_mode(root_path)

if __name__ == "__main__":
    main()
