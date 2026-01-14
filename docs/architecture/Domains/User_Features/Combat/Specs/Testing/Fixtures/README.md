# Fixtures & Mocks

## 🎭 Core Mocks

### `MockActorSnapshot`
Упрощенный билдер для создания актора в тестах.
```python
actor = MockActorSnapshot(hp=100, damage=10).with_weapon("sword").build()
```

### `MockCombatMove`
Билдер для интентов.
```python
move = MockCombatMove(strategy="attack", source="main_hand").build()
```

## 📄 Golden Files
JSON-файлы с эталонными расчетами урона для проверки регрессии.
