"""
Модуль содержит ORM-модели для хранения модификаторов персонажей.

Здесь будут определены модели для различных типов модификаторов,
которые могут быть применены к персонажам, предметам или способностям.
"""

# from sqlalchemy.orm import Mapped, mapped_column
# from database.model_orm.base import Base, TimestampMixin

# class CharacterModifier(Base, TimestampMixin):
#     __tablename__ = "character_modifiers"
#     id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
#     character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id", ondelete="CASCADE"))
#     modifier_key: Mapped[str] = mapped_column(String(50))
#     value: Mapped[float] = mapped_column(Float)
#     source: Mapped[str] = mapped_column(String(50)) # e.g., "item_id:123", "skill_id:456"
