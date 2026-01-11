# 🤖 Google Gemini Integration

⬅️ [Назад](../README.md)

> **Source:** `apps/common/services/gemini_service/`

Сервис для генерации текста с использованием LLM Google Gemini.

## 1. Architecture
Сервис построен на паттерне **Presets & Builders**.

*   **Presets (`MODE_PRESETS`):** Конфигурация режима (температура, макс. токенов, алиас модели).
*   **Builders (`gemini_service_build.py`):** Функции, которые собирают итоговый промпт (System Instruction + User Content) на основе режима.

### Supported Models
*   `fast` -> **gemini-2.0-flash** (Для быстрых ответов, NPC).
*   `pro` -> **gemini-1.5-pro** (Для сложного нарратива).

## 2. Usage

```python
from apps.common.services.gemini_service.gemini_service import gemini_answer
from apps.common.resources.llm_data.mode_preset import ChatMode

# Генерация описания локации
description = await gemini_answer(
    mode=ChatMode.LOCATION_DESC,
    user_text="Мрачный лес с туманом",
    temperature=0.8
)
```

## 3. Configuration
Токен задается в `.env`: `GEMINI_TOKEN`.
Если токен не задан, сервис логирует ошибку, но не роняет приложение (Graceful Degradation).
