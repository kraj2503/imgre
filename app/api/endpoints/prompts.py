from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.database.prompt_repository import PromptRepository
from app.schemas.api_schemas import PromptResponse, PromptDetailResponse

router = APIRouter()

@router.get("/", response_model=List[PromptResponse])
async def list_prompts(
    status: Optional[str] = Query(None, description="Filter prompts by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves list of prompts with optional status filtering and pagination."""
    repo = PromptRepository(db)
    return await repo.get_all(skip=skip, limit=limit, status=status)

@router.get("/{prompt_id}", response_model=PromptDetailResponse)
async def get_prompt(prompt_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieves a single detailed prompt by ID, including associated image variations."""
    repo = PromptRepository(db)
    prompt = await repo.get_by_id(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt
