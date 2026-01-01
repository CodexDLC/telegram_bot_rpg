# Combat DTO Specification (RBC v2.0)

Этот документ описывает структуры данных (DTO), используемые в памяти воркера во время обработки боевого тика.
Мы используем Pydantic для валидации типов.

---

## 📦 1. Входящая Задача (The Bullet)
То, что прилетает из очереди `q:tasks`.

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class CombatInteractionContext(BaseModel):
    """
    Задача на исполнение. 
    Генерируется Менеджером, читается Исполнителем.
    """
    session_id: str
    step_index: int         # Порядковый номер внутри батча (0, 1, 2...)
    
    # Кто и что делает
    source_id: int
    target_id: Optional[int] = None # Может быть None для селф-баффов
    skill_id: str
    
    # Тип задачи (нужен Оркестратору для роутинга)
    interaction_type: str = "exchange" # "exchange", "instant", "effect_tick"
    
    # Доп. параметры (например, ID предмета в инвентаре)
    payload: Dict[str, Any] = {}
```

---

## 📦 2. Состояние Актера (The Actor)
Собирается из 4-х ключей Redis (`:state`, `:raw`, `:cache`, `:effects`).

```python
class ActorState(BaseModel):
    """Изменяемые параметры (Hot Data из Redis HASH)"""
    hp: int
    max_hp: int
    en: int
    max_en: int
    tactics: int = 0
    afk_level: int = 0
    is_dead: bool = False

class ActorStats(BaseModel):
    """Готовые статы для математики (из Redis JSON :cache)"""
    # Атака
    dmg_min: int = 0
    dmg_max: int = 0
    crit_chance: float = 0.0
    crit_power: float = 1.5
    hit_rate: float = 1.0
    
    # Защита
    armor: int = 0
    evasion: float = 0.0
    magic_resist: float = 0.0
    
    # Ресурсы
    vampirism: float = 0.0
    regeneration: int = 0

class ActorEffect(BaseModel):
    """Активный эффект (из Redis JSON :effects)"""
    uid: str              # Уникальный ID наложения (чтобы снять конкретный стак)
    effect_id: str        # "poison_lvl1"
    source_id: int        # Кто наложил (для расчета урона от статов автора)
    expires_at_step: int  # Шаг, на котором эффект исчезнет
    payload: Dict[str, Any] = {} # Снапшот статов (сила яда 50)

class ActorSnapshot(BaseModel):
    """
    Единый объект бойца. 
    Оркестратор работает ТОЛЬКО с ним.
    """
    char_id: int
    team: str             # "red" / "blue"
    
    state: ActorState
    stats: ActorStats
    effects: List[ActorEffect] = []
    
    # Хелпер: Жив ли курилка?
    @property
    def is_alive(self) -> bool:
        return not self.state.is_dead and self.state.hp > 0
```

---

## 📦 3. Глобальный Контекст (The World)
Загружается Воркером один раз на весь батч.

```python
class BattleMeta(BaseModel):
    """Глобальные счетчики (из Redis :meta)"""
    active: int
    step_counter: int         # Текущий шаг (до начала батча)
    active_actors_count: int
    teams: Dict[str, List[int]]
    
    # Конфигурация
    battle_type: str          # "pvp"
    location_id: str

class BattleContext(BaseModel):
    """
    Главный объект, который передается во все сервисы.
    Содержит ВСЮ информацию о текущем состоянии боя.
    """
    session_id: str
    meta: BattleMeta
    actors: Dict[int, ActorSnapshot]
    
    # Очередь логов, которые мы накопили за время обработки батча
    pending_logs: List[Dict] = []
    
    def get_actor(self, char_id: int) -> Optional[ActorSnapshot]:
        return self.actors.get(char_id)
        
    def get_enemies(self, char_id: int) -> List[ActorSnapshot]:
        """Возвращает список живых врагов"""
        me = self.get_actor(char_id)
        if not me: return []
        
        return [
            a for a in self.actors.values() 
            if a.team != me.team and a.is_alive
        ]
```

---

## 📦 4. Результат (Output Log)
То, что мы пишем в `...:logs`.

```python
class LogEntryDTO(BaseModel):
    step: int
    ts: float
    event_type: str       # "damage", "heal", "miss", "death"
    source_id: int
    target_id: Optional[int]
    value: Optional[int]
    html_message: str     # Готовая строка для клиента "<span...>Удар!</span>"
    tags: List[str] = []  # ["crit", "fire"]
```