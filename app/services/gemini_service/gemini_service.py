# app/services/gemini_service/gemini_service.py
import logging
from typing import Any, Optional

from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions

from app.core.config import GEMINI_TOKEN
from app.resources.llm_data.mode_preset import ChatMode, MODE_PRESETS
from app.services.gemini_service.gemini_service_build import BUILDERS_GEMINI as BUILDERS, build_simple_gemini

log = logging.getLogger(__name__)

# Псевдонимы для моделей Gemini для удобства использования.
GEMINI_MODEL_ALIASES = {
    "fast": "gemini-1.5-flash",
    "pro": "gemini-1.5-pro-latest",
}
DEFAULT_MODEL_NAME = GEMINI_MODEL_ALIASES["fast"]

# --- Инициализация клиента ---
# Проверяем наличие токена перед инициализацией.
if not GEMINI_TOKEN:
    log.critical("Токен GEMINI_TOKEN не предоставлен. Сервис Gemini не будет работать.")
    _client = None
else:
    try:
        # Инициализируем асинхронный клиент genai.
        genai.configure(api_key=GEMINI_TOKEN)
        _client = genai.GenerativeModel
        log.info("Клиент Gemini успешно сконфигурирован.")
    except Exception as e:
        log.exception("Не удалось сконфигурировать клиент Gemini.")
        _client = None


async def gemini_answer(mode: ChatMode, user_text: str, **kw: Any) -> str:
    """
    Генерирует ответ с помощью модели Gemini на основе заданного режима и текста.

    Args:
        mode (ChatMode): Режим чата (например, 'npc_speech'), определяющий пресет.
        user_text (str): Текст, предоставленный пользователем или системой.
        **kw: Дополнительные параметры для переопределения пресета (например,
              `temperature`, `max_tokens`, `model`).

    Returns:
        str: Сгенерированный моделью текст или сообщение об ошибке.
    """
    if not _client:
        error_msg = "Клиент Gemini не инициализирован. Проверьте токен API."
        log.error(error_msg)
        return f"Ошибка: {error_msg}"

    preset = MODE_PRESETS.get(mode)
    if not preset:
        error_msg = f"Пресет для режима '{mode}' не найден."
        log.error(error_msg)
        return f"Ошибка: {error_msg}"

    log.info(f"Запрос к Gemini. Режим: '{mode}', Пользовательский текст: '{user_text[:50]}...'")

    # Получаем функцию-сборщик для данного режима или используем сборщик по умолчанию.
    builder_func = BUILDERS.get(mode, build_simple_gemini)
    contents, system_instruction = builder_func(preset, user_text, **kw)
    log.debug(f"Собранные 'contents': {contents!r}")
    log.debug(f"Системная инструкция: {system_instruction!r}")

    # Определяем параметры генерации, отдавая приоритет явно переданным в **kw.
    temperature = float(kw.get("temperature", preset.get("temperature", 0.7)))
    max_tokens = int(kw.get("max_tokens", preset.get("max_tokens", 500)))
    model_alias = kw.get("model_alias", preset.get("model_alias", "fast"))
    model_name = GEMINI_MODEL_ALIASES.get(model_alias, DEFAULT_MODEL_NAME)
    model_name = kw.get("model", model_name) # Явный 'model' имеет наивысший приоритет.

    log.debug(f"Параметры генерации: model='{model_name}', temp={temperature}, max_tokens={max_tokens}")

    try:
        model = _client(model_name)
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )
        # Асинхронно генерируем контент.
        resp = await model.generate_content_async(
            contents=contents,
            generation_config=generation_config,
            system_instruction=system_instruction,
        )
        response_text = resp.text.strip()
        log.info(f"Ответ от Gemini получен. Длина: {len(response_text)} символов.")
        log.debug(f"Полный ответ: '{response_text[:200]}...'")
        return response_text

    except google_exceptions.GoogleAPICallError as e:
        log.error(f"Ошибка API Google при вызове Gemini: {e}")
        return f"Ошибка API: {e.message}"
    except Exception as e:
        log.exception("Неожиданная ошибка при генерации ответа Gemini.")
        return f"Критическая ошибка генерации: {e}"
