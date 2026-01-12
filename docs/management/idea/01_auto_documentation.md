# Idea: Auto-Generated API Documentation

**Status:** Proposed
**Target:** Post-MVP / Stabilization Phase
**Tools:** MkDocs + mkdocstrings (Python)

---

## 1. Проблема
Сейчас документация API (методы, параметры, типы) ведется вручную в Markdown-файлах (`specs/components/*.md`).
Это приводит к рассинхронизации: код меняется, а документация устаревает.

## 2. Решение: Docstrings as Source of Truth
Перенести детальное описание API из Markdown-файлов непосредственно в код (Python Docstrings).

### Пример
Вместо ручного обновления `combat_resolver.md`, мы пишем качественный docstring в коде:

```python
class CombatResolver:
    def calculate_damage(
        self, 
        attacker: ActorSnapshot, 
        defender: ActorSnapshot, 
        context: PipelineContextDTO
    ) -> InteractionResultDTO:
        """
        Рассчитывает финальный урон после всех проверок.
        
        Args:
            attacker: Снапшот атакующего.
            defender: Снапшот защитника.
            context: Контекст удара (флаги, модификаторы).
            
        Returns:
            Результат расчета (урон, флаги, токены).
        """
        ...
```

Затем генератор (MkDocs) автоматически создает HTML-страницу с актуальной сигнатурой.

## 3. Архитектура Документации (Future State)
Документация будет состоять из двух частей:

1.  **Hand-Written (Architecture):**
    *   Концепции, схемы потоков (Mermaid), манифесты.
    *   Отвечает на вопрос "КАК и ЗАЧЕМ это работает?".
    *   Хранится в `docs/architecture/`.

2.  **Auto-Generated (API Reference):**
    *   Списки классов, методов, аргументов.
    *   Отвечает на вопрос "ЧТО принимает этот метод?".
    *   Генерируется из кода `apps/`.

## 4. План внедрения
1.  **Стабилизация API:** Дождаться завершения активного рефакторинга боевой системы (v3.1).
2.  **Docstring Standard:** Принять стандарт (Google Style или NumPy Style) и начать писать docstrings для новых методов.
3.  **Setup MkDocs:** Настроить `mkdocs.yml` и плагин `mkdocstrings`.
4.  **CI/CD:** Настроить сборку документации при пуше в мастер.
