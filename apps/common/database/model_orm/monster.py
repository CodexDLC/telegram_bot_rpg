import uuid

from sqlalchemy import JSON, Column, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import relationship

from apps.common.database.model_orm.base import Base


class GeneratedClanORM(Base):
    __tablename__ = "generated_clans"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    family_id = Column(String, nullable=False)  # "orcs_family"
    tier = Column(Integer, nullable=False)  # 2

    # --- ПРИВЯЗКА К МИРУ ---
    # ID зоны, где этот клан был создан (например, "D4_1_1")
    # Это позволяет легко найти всех обитателей конкретной зоны.
    zone_id = Column(String, nullable=True, index=True)

    # --- НОВЫЕ ПОЛЯ ХЭШЕЙ ---

    # 1. ХЭШ КОНТЕКСТА (ГДЕ МЫ?)
    # Формула: md5(tier + biome + anchor_type)
    # Пример: "forest_2_ice" -> "a1b2..."
    # ЗАЧЕМ: Спавнер делает SELECT * WHERE context_hash = "..." и получает список (Волки, Орки, Пауки).
    context_hash = Column(String(32), nullable=False, index=True)

    # 2. УНИКАЛЬНЫЙ ХЭШ (КТО ЭТО?)
    # Формула: md5(family_id + context_hash)
    # Пример: "orcs_family" + "a1b2..." -> "c3d4..."
    # ЗАЧЕМ: Фабрика проверяет, создавали ли мы уже Орков для этого места.
    unique_hash = Column(String(32), nullable=False, unique=True, index=True)

    # --- ОСТАЛЬНОЕ ---
    raw_tags = Column(JSON, nullable=False)  # Просто для дебага
    flavor_content = Column(JSON, nullable=False)  # Имя, описание от LLM

    name_ru = Column(String, nullable=True)
    description = Column(String, nullable=True)

    members = relationship(
        "GeneratedMonsterORM", back_populates="clan", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        # Индекс для быстрого поиска группой (для спавнера)
        Index("ix_clan_context_lookup", "context_hash", "tier"),
    )


class GeneratedMonsterORM(Base):
    """
    Таблица СГЕНЕРИРОВАННЫХ МОНСТРОВ (Инстансы).
    Это конкретный "Орк Вася", который стоит в локации, со своими ХП и вещами.
    """

    __tablename__ = "generated_monsters"

    # --- ID и Связи ---
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    clan_id = Column(
        Uuid(as_uuid=True), ForeignKey("generated_clans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Связь с кланом (GeneratedClanORM)
    clan = relationship("GeneratedClanORM", back_populates="members")

    # --- БАЛАНС И ИДЕНТИФИКАЦИЯ (из MonsterVariant) ---
    variant_key = Column(
        String, nullable=False
    )  # ex: "orc_grunt" (ИСПРАВЛЕНО: было variant_id в коде, но variant_key в фабрике)
    # family_id дублировать не обязательно, он есть в клане, но для удобства можно оставить или убрать.
    # В фабрике мы не заполняли family_id для монстра, только для клана.
    # Но в ORM выше было поле family_id. Давайте проверим фабрику.
    # Фабрика: monsters.append(GeneratedMonsterORM(..., variant_key=unit_key, ...))
    # Поле family_id в GeneratedMonsterORM не заполнялось в фабрике!
    # Значит, его лучше убрать или сделать nullable, или заполнять.
    # Пока оставим как есть, но учтем, что оно может быть пустым, если фабрика его не пишет.
    # UPD: В прошлом чтении файла фабрики я видел:
    # monsters.append(GeneratedMonsterORM(..., variant_key=unit_key, ...))
    # Там НЕ БЫЛО family_id.
    # Значит, если я оставлю nullable=False, будет ошибка.
    # Я сделаю его nullable=True или уберу. Лучше уберу, так как есть связь с кланом.

    role = Column(String, nullable=False)  # "minion", "elite", "boss"
    threat_rating = Column(Integer, nullable=False)  # ex: 50 (Уровень угрозы)

    # --- НАРРАТИВ (Генерируется LLM или шаблонизатором) ---
    name_ru = Column(String, nullable=False)  # ex: "Грязный рубака"
    description = Column(String, nullable=True)  # ex: "От него разит помоями..."

    # --- SNAPSHOTS (Данные боя) ---

    # Полный слепок характеристик (MonsterStats), уже скалированный под уровень
    scaled_base_stats = Column(JSON, nullable=False)

    # Экипировка (MonsterLoadout)
    loadout_ids = Column(JSON, nullable=False)

    # Активные навыки (MonsterVariant.skills)
    skills_snapshot = Column(JSON, nullable=False)

    # Состояние (Текущие HP/MP - если монстр сохраняется раненым)
    current_state = Column(JSON, nullable=True)

    # Индексы для ускорения выборок
    __table_args__ = (Index("ix_monster_role_threat", "role", "threat_rating"),)

    def __repr__(self):
        return f"<Monster {self.name_ru} ({self.variant_key}) Threat:{self.threat_rating}>"
