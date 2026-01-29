# run.py
"""
Универсальный запускатель для сервисов проекта.

Usage:
    python run.py backend  # Запуск Backend API (FastAPI)
    python run.py bot      # Запуск Telegram Bot клиента

Автоматически добавляет корень проекта в PYTHONPATH.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    """Главная функция запуска сервисов."""
    if len(sys.argv) < 2:
        print("❌ Error: Service name required")
        print("\nUsage:")
        print("  python run.py backend  # Start Backend API (FastAPI)")
        print("  python run.py bot      # Start Telegram Bot client")
        sys.exit(1)

    service = sys.argv[1].lower()

    if service == "backend":
        print("🚀 Starting Backend API...")
        import uvicorn

        # reload=False для стабильной работы Ctrl+C на Windows и ускорения старта
        # Включите reload=True, если нужна авто-перезагрузка при изменении кода
        uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")

    elif service == "bot":
        print("🤖 Starting Telegram Bot...")
        from src.frontend.telegram_bot.app_telegram import main as bot_main

        try:
            asyncio.run(bot_main())
        except (KeyboardInterrupt, SystemExit):
            print("\n👋 Bot stopped by user")
        except Exception as e:  # noqa: BLE001
            print(f"\n❌ Critical error: {e}")
            sys.exit(1)

    else:
        print(f"❌ Error: Unknown service '{service}'")
        print("\nAvailable services:")
        print("  - backend  (Backend API)")
        print("  - bot      (Telegram Bot)")
        sys.exit(1)


if __name__ == "__main__":
    main()
