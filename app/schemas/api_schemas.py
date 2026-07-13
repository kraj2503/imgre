from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class ArtGenerationRequest(BaseModel):
    """Schema for requesting a new optimized prompt and image variation."""
    user_idea: Optional[str] = None
    user_edits: Optional[str] = None
    session_id: Optional[str] = None

class ImageResponse(BaseModel):
    """Schema for Image record response."""
    id: int
    prompt_id: int
    file_path: str
    status: str
    score: Optional[float] = None
    is_best: bool
    meta_data: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PromptResponse(BaseModel):
    """Schema for Prompt record response."""
    id: int
    title: str
    prompt: str
    version: int
    trend_summary: Optional[Any] = None
    aesthetic_score: Optional[float] = None
    psychology_score: Optional[float] = None
    attempts: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class PromptDetailResponse(PromptResponse):
    """Schema for Prompt response including associated images."""
    images: List[ImageResponse] = []

class ArtGenerationResponse(BaseModel):
    """Schema representing the combined final outputs of the loop execution."""
    prompt: PromptResponse
    images: List[ImageResponse] = []
    best_image_id: Optional[int] = None
    best_image_url: Optional[str] = None
