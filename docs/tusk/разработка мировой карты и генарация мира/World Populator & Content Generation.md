3. World Populator & Content Generation.md (Генерация контента)
Статус: ⚠️ Реализовано частично / Адаптировано.

Триггер генерации:

Док: Генерация по триггеру квеста (Quest Trigger).

Код: Сейчас реализована генерация при посеве мира (scripts/seed_world_gen.py -> Stage 5: AI Generation) для прокладки дорог от Хаба. Квестового сервиса, вызывающего генератор, в явном виде пока нет, но ContentGenerationService готов к этому (метод generate_content_for_path).

Skeleton JSON & LLM:

В коде: ContentGenerationService собирает internal_tags и surroundings (окружение) и отправляет это в Gemini (режим batch_location_desc). Это соответствует архитектуре "Технический JSON -> Художественный текст".
