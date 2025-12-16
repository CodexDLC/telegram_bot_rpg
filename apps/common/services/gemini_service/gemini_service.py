from typing import Any

from google import genai
from google.auth import exceptions
from google.genai import errors, types
from loguru import logger as log

from apps.common.core.settings import settings
from apps.common.resources.llm_data.mode_preset import MODE_PRESETS, ChatMode
from apps.common.services.gemini_service.gemini_service_build import (
    BUILDERS_GEMINI as BUILDERS,
)
from apps.common.services.gemini_service.gemini_service_build import (
    build_simple_gemini,
)

# 🔥 FIX 1: Точные названия моделей. SDK требует полные ID.
GEMINI_MODEL_ALIASES = {
    "fast": "gemini-2.0-flash",
    "pro": "gemini-1.5-pro-001",
}
DEFAULT_MODEL_NAME = GEMINI_MODEL_ALIASES["fast"]

_client: genai.Client | None = None
if not settings.gemini_token:
    log.critical("GeminiClient | status=failed reason='GEMINI_TOKEN not provided'")
else:
    try:
        _client = genai.Client(api_key=settings.gemini_token)
        log.info("GeminiClient | status=initialized")
    except (errors.ClientError, ValueError) as e:
        log.exception(f"GeminiClient | status=failed reason='Initialization error' error='{e}'")


async def gemini_answer(mode: ChatMode, user_text: str, **kw: Any) -> str:
    """
    Генерирует ответ с помощью модели Gemini, используя заданный режим и текст пользователя.

    Args:
        mode: Режим чата, определяющий пресет настроек и функцию-сборщик промпта.
        user_text: Основной текст пользователя, который будет включен в промпт.
        **kw: Дополнительные параметры (temperature, max_tokens, model_alias).

    Returns:
        Сгенерированный текстовый ответ.
    """
    if not _client:
        error_msg = "GeminiAnswer | status=failed reason='Client not initialized'"
        log.error(error_msg)
        return f"Ошибка: {error_msg}"

    preset = MODE_PRESETS.get(mode)
    if not preset:
        error_msg = f"GeminiAnswer | status=failed reason='Preset not found' mode='{mode}'"
        log.error(error_msg)
        return f"Ошибка: {error_msg}"

    log.info(f"GeminiAnswer | event=request mode='{mode}'")

    builder_func = BUILDERS.get(mode, build_simple_gemini)
    contents, system_instruction = builder_func(preset, user_text, **kw)

    temperature = float(kw.get("temperature", preset.get("temperature", 0.7)))
    max_tokens = int(kw.get("max_tokens", preset.get("max_tokens", 500)))
    model_alias = kw.get("model_alias", preset.get("model_alias", "fast"))
    model_name = GEMINI_MODEL_ALIASES.get(model_alias, DEFAULT_MODEL_NAME)
    model_name = kw.get("model", model_name)

    config = types.GenerateContentConfig(
        temperature=temperature, max_output_tokens=max_tokens, system_instruction=system_instruction
    )

    try:
        resp = await _client.aio.models.generate_content(model=model_name, contents=contents, config=config)
        response_text = resp.text.strip() if resp.text else ""
        log.info(f"GeminiAnswer | status=success mode='{mode}' response_length={len(response_text)}")
        return response_text

    except errors.ClientError as e:
        # 🔥 FIX 2: Безопасное логирование.
        # Мы не суем {e} внутрь f-строки логгера, так как 'e' содержит JSON с фигурными скобками,
        # что ломает форматирование Loguru (вызывая KeyError: 'error').
        log.error(f"GeminiAnswer | status=failed reason='Google API ClientError' mode='{mode}'")
        log.error(f"API Error Trace: {e}")
        return f"Ошибка API: {e}"

    except exceptions.DefaultCredentialsError as e:
        log.exception(f"GeminiAnswer | status=failed reason='Unexpected error' mode='{mode}' error='{e}'")
        return f"Критическая ошибка генерации: {e}"
