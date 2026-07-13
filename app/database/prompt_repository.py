from typing import List, Optional, Any, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.prompt import Prompt
from app.models.image import Image

class PromptRepository:
    """Asynchronous CRUD Repository for Prompt models."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, title: str, prompt: str, **kwargs) -> Prompt:
        """Create a new prompt record."""
        db_prompt = Prompt(
            title=title,
            prompt=prompt,
            version=kwargs.get("version", 1),
            trend_summary=kwargs.get("trend_summary"),
            aesthetic_score=kwargs.get("aesthetic_score"),
            psychology_score=kwargs.get("psychology_score"),
            attempts=kwargs.get("attempts", 0),
            status=kwargs.get("status", "pending"),
        )
        self.session.add(db_prompt)
        await self.session.commit()
        await self.session.refresh(db_prompt)
        return db_prompt

    async def get_by_id(self, prompt_id: int) -> Optional[Prompt]:
        """Fetch a single prompt by its ID."""
        return await self.session.get(Prompt, prompt_id)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Prompt]:
        """Fetch multiple prompts with optional pagination and status filtering."""
        query = select(Prompt)
        if status:
            query = query.filter(Prompt.status == status)
        query = query.offset(skip).limit(limit).order_by(Prompt.id.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_approved_prompts_without_images(self) -> List[Prompt]:
        """Fetch all approved prompts that do not have any associated image variations yet."""
        query = select(Prompt).filter(Prompt.status == "approved").filter(~Prompt.images.any())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, prompt_id: int, update_data: Dict[str, Any]) -> Optional[Prompt]:
        """Update fields of an existing prompt."""
        db_prompt = await self.get_by_id(prompt_id)
        if not db_prompt:
            return None

        for key, value in update_data.items():
            if hasattr(db_prompt, key):
                setattr(db_prompt, key, value)

        await self.session.commit()
        await self.session.refresh(db_prompt)
        return db_prompt

    async def delete(self, prompt_id: int) -> bool:
        """Delete a prompt record."""
        db_prompt = await self.get_by_id(prompt_id)
        if not db_prompt:
            return False

        await self.session.delete(db_prompt)
        await self.session.commit()
        return True

    async def increment_attempts(self, prompt_id: int) -> Optional[Prompt]:
        """Utility to safely increment execution attempts."""
        db_prompt = await self.get_by_id(prompt_id)
        if db_prompt:
            db_prompt.attempts += 1
            await self.session.commit()
            await self.session.refresh(db_prompt)
        return db_prompt
