from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.database.image_repository import ImageRepository
from app.schemas.api_schemas import ImageResponse

router = APIRouter()

@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(image_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieves a single image variation metadata by its ID."""
    repo = ImageRepository(db)
    image = await repo.get_by_id(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image variation not found")
    return image

@router.get("/prompt/{prompt_id}", response_model=List[ImageResponse])
async def list_images_by_prompt(prompt_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieves all image variations associated with a specific prompt ID."""
    repo = ImageRepository(db)
    return await repo.get_by_prompt_id(prompt_id)
