from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Float, Integer, Boolean, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_best: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Map Python's 'meta_data' class attribute to column 'metadata' in PostgreSQL
    meta_data: Mapped[Optional[Any]] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    # Relationship to parent prompt
    prompt: Mapped["Prompt"] = relationship("Prompt", back_populates="images")

    def __repr__(self) -> str:
        return f"<Image id={self.id} prompt_id={self.prompt_id} is_best={self.is_best}>"
