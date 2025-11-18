from typing import Any

from google import genai
from google.genai import (
    errors,  # Ошибки нового SDK
    types,  # Типы для конфигов
)
from loguru import logger as log

from app.core.config import GEMINI_TOKEN
from app.resources.llm_data.mode_preset import MODE_PRESETS, ChatMode
from app.services.gemini_service.gemini_service_build import BUILDERS_GEMINI as BUILDERS
from app.services.gemini_service.gemini_service_build import build_simple_gemini

# Псевдонимы для моделей (в новом SDK названия такие же, но лучше указывать явно)
GEMINI_MODEL_ALIASES = {
    "fast": "gemini-1.5-flash",
    "pro": "gemini-1.5-pro-latest",
}
DEFAULT_MODEL_NAME = GEMINI_MODEL_ALIASES["fast"]

# --- Инициализация клиента (НОВЫЙ SDK) ---
# В google-genai нет метода configure(). Мы создаем Client().
if not GEMINI_TOKEN:
    log.critical("Токен GEMINI_TOKEN не предоставлен. Сервис Gemini не будет работать.")
    _client = None
else:
    try:
        # Инициализируем клиент напрямую
        _client = genai.Client(api_key=GEMINI_TOKEN)
        log.info("Клиент Gemini (New SDK) успешно создан.")
    except Exception as e:  # noqa: BLE001
        log.exception(f"Не удалось создать клиент Gemini: {e}")
        _client = None


async def gemini_answer(mode: ChatMode, user_text: str, **kw: Any) -> str:
    """
    Генерирует ответ с помощью модели Gemini (Новый SDK).
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

    log.info(f"Запрос к Gemini. Режим: '{mode}'")

    # Сборка промпта
    builder_func = BUILDERS.get(mode, build_simple_gemini)
    contents, system_instruction = builder_func(preset, user_text, **kw)

    # Параметры генерации
    temperature = float(kw.get("temperature", preset.get("temperature", 0.7)))
    max_tokens = int(kw.get("max_tokens", preset.get("max_tokens", 500)))
    model_alias = kw.get("model_alias", preset.get("model_alias", "fast"))
    model_name = GEMINI_MODEL_ALIASES.get(model_alias, DEFAULT_MODEL_NAME)
    model_name = kw.get("model", model_name)

    # --- НОВЫЙ SDK: Конфигурация ---
    # В google-genai системная инструкция и параметры передаются в config
    config = types.GenerateContentConfig(
        temperature=temperature, max_output_tokens=max_tokens, system_instruction=system_instruction
    )

    try:
        # --- НОВЫЙ SDK: Асинхронный вызов ---
        # Используем _client.aio.models.generate_content
        resp = await _client.aio.models.generate_content(model=model_name, contents=contents, config=config)

        response_text = resp.text.strip() if resp.text else ""
        log.info(f"Ответ от Gemini получен. Длина: {len(response_text)} символов.")
        return response_text

    except errors.ClientError as e:
        log.error(f"Ошибка API Google (ClientError): {e}")
        return f"Ошибка API: {e}"
    except Exception as e:  # noqa: BLE001
        log.exception("Неожиданная ошибка при генерации ответа Gemini.")
        return f"Критическая ошибка генерации: {e}"
