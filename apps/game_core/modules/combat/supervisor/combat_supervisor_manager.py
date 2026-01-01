# apps/game_core/modules/combat/supervisor/combat_supervisor_manager.py
"""
Файл: apps/game_core/modules/combat/supervisor/combat_supervisor_manager.py
"""

import asyncio

from loguru import logger as log

# Глобальный словарь для хранения активных задач супервизоров.
# Ключ: session_id, Значение: asyncio.Task
_active_supervisors: dict[str, asyncio.Task] = {}


def add_supervisor_task(session_id: str, task: asyncio.Task):
    """
    Регистрирует таску и вешает колбэк на самоочистку.
    """
    if session_id in _active_supervisors:
        log.warning(f"SupervisorManager | Overwriting existing task for session {session_id}")

    _active_supervisors[session_id] = task

    def _cleanup(t):
        # Проверяем, что удаляем именно ту таску, которая завершилась
        # (на случай, если уже перезаписали новой)
        if _active_supervisors.get(session_id) == t:
            _active_supervisors.pop(session_id, None)
            log.debug(f"SupervisorManager | Task cleanup for session {session_id}")

    task.add_done_callback(_cleanup)
    log.debug(f"SupervisorManager | Task added for session {session_id}")


def get_supervisor_task(session_id: str) -> asyncio.Task | None:
    """Возвращает задачу супервизора по ID сессии."""
    return _active_supervisors.get(session_id)


def remove_supervisor_task(session_id: str):
    """Явное удаление задачи из реестра."""
    _active_supervisors.pop(session_id, None)


def stop_supervisor(session_id: str):
    """Принудительная остановка боя."""
    task = _active_supervisors.get(session_id)
    if task and not task.done():
        task.cancel()
        log.info(f"SupervisorManager | Task cancelled for session {session_id}")


def get_active_supervisor_count() -> int:
    """Возвращает количество активных супервизоров."""
    return len(_active_supervisors)
