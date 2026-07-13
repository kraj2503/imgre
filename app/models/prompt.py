from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy import String, Text, Float, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    trend_summary: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    aesthetic_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    psychology_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    # One-to-many relationship with generated image variations
    images: Mapped[List["Image"]] = relationship(
        "Image",
        back_populates="prompt",
        cascade="all, delete-orphan",
        lazy="selectin"  # Prefetches children in an efficient subquery
    )

    def __repr__(self) -> str:
        return f"<Prompt id={self.id} title={self.title!r} status={self.status!r}>"
