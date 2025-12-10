import os


def generate_project_tree():
    """
    Генерирует текстовый файл со структурой проекта, игнорируя ненужные папки и файлы.
    """
    # Определяем корень проекта (родитель папки scripts)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    output_filename = os.path.join(project_root, "project_structure.txt")

    # Папки и файлы, которые нужно игнорировать
    ignore_dirs = {
        ".git",
        "venv",
        ".venv",
        "__pycache__",
        ".idea",
        ".vscode",
        "data",
        "logs",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".gemini",
    }
    ignore_files_extensions = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".db", ".sqlite3"}

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(f"Project Structure for: {os.path.basename(project_root)}\n\n")

        for root, dirs, files in os.walk(project_root, topdown=True):
            # Исключаем папки из дальнейшего обхода
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            # Пропускаем саму корневую папку в выводе, чтобы не было лишнего отступа
            level = 0 if root == project_root else root.replace(project_root, "").count(os.sep)

            indent = " " * 4 * level
            f.write(f"{indent}📂 {os.path.basename(root)}/\n")

            sub_indent = " " * 4 * (level + 1)
            for file in sorted(files):
                if not any(file.endswith(ext) for ext in ignore_files_extensions):
                    f.write(f"{sub_indent}📄 {file}\n")

    print(f"✅ Файл '{output_filename}' успешно создан!")


if __name__ == "__main__":
    generate_project_tree()
