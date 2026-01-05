# Combat DTO Specification (RBC v3.0)

Этот документ является **Единым Источником Истины** для всех Python-классов (DTO), используемых в боевой системе.
Файл реализации: `apps/common/schemas_dto/combat_source_dto.py`.

---

## 1. Payloads (TypedDict)
Специализированные структуры данных для разных типов действий. Хранятся внутри `CombatMoveDTO.payload`.

### A. ItemPayload
Используется для стратегии `item`.
```python
class ItemPayload(TypedDict):
    item_id: int
    target_id: Union[int, str]  # ID цели или инструкция ("self", "all_enemies")
```

### B. InstantPayload
Используется для стратегии `instant` (Скиллы).
```python
class InstantPayload(TypedDict):
    skill_id: str
    target_id: Union[int, str]
```

### C. ExchangePayload
Используется для стратегии `exchange` (Боевой контакт).
```python
class ExchangePayload(TypedDict):
    target_id: int              # Конкретный ID оппонента
    attack_zones: List[str]     # ["head"]
    block_zones: List[str]      # ["body", "legs"]
    
    # Опционально (чем бьем)
    skill_id: Optional[str]
    item_id: Optional[int]      # Если это граната/метательное в бою
```

---

## 2. Ingress DTOs (Router -> Redis)

### CombatMoveDTO (The Bullet)
Основной объект намерения, хранящийся в RedisJSON (`moves:{char_id}`).

```python
class CombatMoveDTO(BaseModel):
    move_id: str            # Unique Short ID
    char_id: int            # Кто ходит
    
    # Зона хранения и Логика обработки
    strategy: str           # "item" | "instant" | "exchange"
    
    created_at: float       # Timestamp
    
    # Полиморфный контейнер данных
    payload: Dict[str, Any] # ItemPayload | InstantPayload | ExchangePayload
    
    # Результат резолвинга целей (заполняется Колектором)
    targets: Optional[List[int]] = None
```

### CollectorSignalDTO
Сигнал для триггера Колектора.
```python
class CollectorSignalDTO(BaseModel):
    session_id: str
    char_id: int
    signal_type: str        # "check_immediate" | "check_timeout" | "heartbeat"
    move_id: Optional[str]
```

### SessionDataDTO (Initialization)
Контейнер для пакетного создания сессии.
```python
class SessionDataDTO(BaseModel):
    meta: Dict[str, Any]
    actors: Dict[str, Dict[str, Any]] # {char_id: {state, raw, ...}}
    targets: Dict[int, List[int]]
```

---

## 3. Orchestration DTOs (Manager -> Worker)

### CombatActionDTO (The Task)
Задача для Воркера в очереди `q:actions`.
Содержит полные данные мува (Cut & Paste), чтобы Исполнителю не нужно было обращаться к `moves`.

```python
class CombatActionDTO(BaseModel):
    action_type: str        # "item", "instant", "exchange", "forced"
    
    # Основной мув (Инициатор)
    move: CombatMoveDTO
    
    # Ответный мув (для exchange)
    partner_move: Optional[CombatMoveDTO] = None 
    
    is_forced: bool = False
```

### AiTurnRequestDTO
Задача для AI Worker.
```python
class AiTurnRequestDTO(BaseModel):
    session_id: str
    bot_id: int
    # Список целей, которые бот ОБЯЗАН атаковать (чтобы закрыть очередь)
    missing_targets: List[int] = []
```

---

## 4. Runtime Context DTOs (Worker Memory)

### ActorState (Hot Data)
Изменяемые параметры из Redis Hash `:state`.
```python
class ActorState(BaseModel):
    hp: int
    max_hp: int
    en: int
    max_en: int
    tactics: int
    afk_level: int
    is_dead: bool
    exchange_count: int
    tokens: Dict[str, int]  # {"gift": 1, "parry": 1}
```

### ActorRawDTO (Cold Data)
Строгая типизация для `:raw` данных.
```python
class ActorRawDTO(BaseModel):
    attributes: Dict[str, Any]
    modifiers: Dict[str, Any]
    
    # Whitelist доступных абилок
    known_abilities: List[str]
    
    # Маппинг экипировки для XP сервиса
    # {"main_hand": "light_weapons", "head_armor": "heavy_armor"}
    equipment_layout: Dict[str, str]
```

### ActiveAbilityDTO (Dynamic Modifiers)
Активные эффекты из Redis JSON `:active_abilities`.
```python
class ActiveAbilityDTO(BaseModel):
    uid: str
    ability_id: str
    source_id: int
    expire_at_exchange: int  # Таймер жизни (в разменах)
    impact: Dict[str, int]   # {"hp": -10}
    payload: Dict[str, Any]
```

### ActorSnapshot (The Root)
Агрегатор данных актера в памяти.
```python
class ActorSnapshot(BaseModel):
    char_id: int
    team: str
    
    state: ActorState
    
    # Calculated (In-Memory only)
    # Может быть None, если еще не посчитан в этом цикле
    stats: Optional[ActorStats] = None 
    
    # Optimization: Dirty Flags
    # Список полей, которые изменились в :raw и требуют пересчета
    dirty_stats: Set[str] = Field(default_factory=set)
    
    active_abilities: List[ActiveAbilityDTO]
    raw: ActorRawDTO        # Typed Source
    xp_buffer: Dict[str, int] # Accumulator
```

---

## 5. Output DTOs (Results)

### InteractionResultDTO
Результат работы Калькулятора.
```python
class InteractionResultDTO(BaseModel):
    damage_final: int
    shield_dmg: int
    lifesteal_amount: int
    thorns_damage: int
    
    is_crit: bool
    is_blocked: bool
    is_dodged: bool
    is_miss: bool
    is_counter: bool
    
    tokens_atk: Dict[str, int]
    tokens_def: Dict[str, int]
    
    logs: List[str]
```

---

## 7. 🖥️ UI / DASHBOARD (Client View)

### CombatLogEntryDTO
Одна запись лога.
```python
class CombatLogEntryDTO(BaseModel):
    text: str
    timestamp: float
    tags: List[str] = []
```

### ActorShortInfo
Минимальная информация для списков (Allies/Enemies).
```python
class ActorShortInfo(BaseModel):
    char_id: int
    name: str
    hp_percent: int
    is_dead: bool
    is_target: bool = False # Выделение в списке
```

### ActorFullInfo
Полная информация для Героя и Цели.
```python
class ActorFullInfo(BaseModel):
    char_id: int
    name: str
    team: str
    
    # Строка 1
    hp_current: int
    hp_max: int
    energy_current: int
    energy_max: int
    
    # Для кнопок
    weapon_type: str # "sword", "bow", "staff" (из main_hand)
    
    # Строка 2 (Tokens)
    tokens: Dict[str, int] # {"tactics": 5, "gift": 1}
    
    # Строка 3 (Status)
    effects: List[str] # ["burn", "stun"] (ID иконок)
```

### CombatDashboardDTO
Полный снимок экрана боя.
```python
class CombatDashboardDTO(BaseModel):
    turn_number: int
    status: str # "active" | "waiting" | "finished"
    
    # Блок 1: Я
    hero: ActorFullInfo
    
    # Блок 2: Цель (если есть)
    target: Optional[ActorFullInfo] = None
    
    # Блок 3: Списки (для контекста)
    allies: List[ActorShortInfo]
    enemies: List[ActorShortInfo]
    
    winner_team: Optional[str] = None

    logs: List[CombatLogEntryDTO] = []
```

### CombatLogDTO
Логи с пагинацией.
```python
class CombatLogDTO(BaseModel):
    logs: List[CombatLogEntryDTO]
    total: int
    page: int
```
