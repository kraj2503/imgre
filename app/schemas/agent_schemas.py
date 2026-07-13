from pydantic import BaseModel, Field
from typing import List, Optional

class TrendAnalysisOutput(BaseModel):
    """Output schema for the Trend Research Agent."""
    theme: str = Field(description="Core thematic style (e.g., Cyberpunk, Organic Minimalism)")
    lighting: str = Field(description="Lighting style and direction (e.g., Rim lighting, Golden hour)")
    fashion: str = Field(description="Fashion, attire, and costume details")
    colors: List[str] = Field(description="Hex colors or names representing the dominant color palette")
    composition: str = Field(description="Composition strategy (e.g., Rule of thirds, Centered portrait)")
    camera: str = Field(description="Camera and lens details (e.g., 85mm f/1.4 lens)")
    background: str = Field(description="Background and environment descriptions")
    recommendations: List[str] = Field(description="Actionable prompt keywords and visual styling advice")

class PromptGenerationOutput(BaseModel):
    """Output schema for the Prompt Generation Agent."""
    title: str = Field(description="Short, descriptive title for the prompt")
    prompt: str = Field(description="Highly detailed descriptive prompt optimized for image generation models")
    negative_prompt: Optional[str] = Field(None, description="Optional negative prompt detailing elements to avoid")

class ReviewOutput(BaseModel):
    """Output schema for the Aesthetic and Psychology Prompt/Image Review Agents."""
    score: float = Field(description="Numerical evaluation score from 0 to 100")
    approved: bool = Field(description="Boolean indicating if the prompt/image meets the passing threshold")
    feedback: List[str] = Field(description="Specific visual or psychological critiques and optimization feedback")

class RankingOutput(BaseModel):
    """Output schema for the Image Ranking Agent."""
    selected_image_id: int = Field(description="The unique database ID of the selected best variation")
    ranking: List[int] = Field(description="Ordered list of database IDs of image variations, ranked from best to worst")
