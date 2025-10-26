# app/services/gemini_service/gemini_service.py
import logging
from typing import Any
from google import genai
from google.genai import types

from app.core.config import GEMINI_TOKEN
from app.resources.llm_data.mode_preset import ChatMode, MODE_PRESETS

from app.services.gemini_service.gemini_service_build import BUILDERS_GEMINI as BUILDERS, build_simple_gemini

log = logging.getLogger(__name__)

GEMINI_MODEL_DEFAULT = "gemini-2.5-flash-lite" # или "gemini-2.5-pro"

_client = genai.Client(
    api_key=GEMINI_TOKEN,
    # для Developer API явная версия (см. твою доку)
    http_options=types.HttpOptions(api_version="v1alpha"),
)

def _gen_cfg(temperature: float, max_tokens: int) -> dict:
    return {"temperature": float(temperature), "max_output_tokens": int(max_tokens)}

async def gemini_answer(mode: ChatMode, user_text: str, **kw: Any) -> str:
    preset = MODE_PRESETS[mode]
    log.info(f"Выбран preset: {mode}")
    builder_func = BUILDERS.get(mode) or build_simple_gemini

    contents, system_instruction = builder_func(preset, user_text, **kw)
    log.debug(f"Собранные contents: {contents!r}")

    temperature = kw.get("temperature", preset["temperature"])
    max_tokens  = kw.get("max_tokens",  preset["max_tokens"])
    model       = kw.get("model", GEMINI_MODEL_DEFAULT)

    try:
        resp = await _client.aio.models.generate_content(
            model=model,
            contents=contents,
            # ⬇️ ВАЖНО: все настройки, включая system_instruction, идут через config=
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=float(temperature),
                max_output_tokens=int(max_tokens),
            ),
        )
        return getattr(resp, "text", "") or ""
    except Exception as e:
        log.exception("Gemini error")
        return f"Ошибка генерации: {e}"
