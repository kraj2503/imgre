from typing import List, Optional, Any, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.image import Image

class ImageRepository:
    """Asynchronous CRUD Repository for Image models."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, prompt_id: int, file_path: str, **kwargs) -> Image:
        """Create a new image record linked to a prompt."""
        db_image = Image(
            prompt_id=prompt_id,
            file_path=file_path,
            status=kwargs.get("status", "pending"),
            score=kwargs.get("score"),
            is_best=kwargs.get("is_best", False),
            meta_data=kwargs.get("metadata"),  # maps to the metadata table column
        )
        self.session.add(db_image)
        await self.session.commit()
        await self.session.refresh(db_image)
        return db_image

    async def get_by_id(self, image_id: int) -> Optional[Image]:
        """Fetch a single image by its ID."""
        return await self.session.get(Image, image_id)

    async def get_by_prompt_id(self, prompt_id: int) -> List[Image]:
        """Fetch all images associated with a specific prompt."""
        query = select(Image).filter(Image.prompt_id == prompt_id).order_by(Image.id.asc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, image_id: int, update_data: Dict[str, Any]) -> Optional[Image]:
        """Update fields of an existing image."""
        db_image = await self.get_by_id(image_id)
        if not db_image:
            return None

        for key, value in update_data.items():
            # If update key is metadata, assign it to model's meta_data attribute
            model_key = "meta_data" if key == "metadata" else key
            if hasattr(db_image, model_key):
                setattr(db_image, model_key, value)

        await self.session.commit()
        await self.session.refresh(db_image)
        return db_image

    async def set_best_image(self, image_id: int) -> Optional[Image]:
        """Mark an image as 'is_best' for its prompt and disable all sibling images' flags."""
        target_image = await self.get_by_id(image_id)
        if not target_image:
            return None

        prompt_id = target_image.prompt_id
        sibling_images = await self.get_by_prompt_id(prompt_id)
        for img in sibling_images:
            img.is_best = (img.id == image_id)

        await self.session.commit()
        await self.session.refresh(target_image)
        return target_image

    async def delete(self, image_id: int) -> bool:
        """Delete an image record."""
        db_image = await self.get_by_id(image_id)
        if not db_image:
            return False

        await self.session.delete(db_image)
        await self.session.commit()
        return True
