from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class AgentWorkflowState(BaseModel):
    """Shared state model representing the context of our multi-agent pipeline.

    This state is maintained across agents by Google ADK session state management.
    """
    user_id: str
    session_id: str

    # Trend Research
    trends_analyzed: bool = False
    trend_summary: Optional[Dict[str, Any]] = None
    trend_tags: List[str] = Field(default_factory=list)

    # Prompt Engineering Loop
    prompt_candidate_title: Optional[str] = None
    prompt_candidate_text: Optional[str] = None
    prompt_attempt_count: int = 0
    prompt_feedback_history: List[Dict[str, Any]] = Field(default_factory=list)
    prompt_approved: bool = False
    prompt_id_saved: Optional[int] = None

    # Prompt Review Metrics
    aesthetic_score: float = 0.0
    psychology_score: float = 0.0

    # Image Pipeline State
    image_pipeline_triggered: bool = False
    prompts_processed: List[int] = Field(default_factory=list)
    image_variations: List[Dict[str, Any]] = Field(default_factory=list)
    selected_best_image_id: Optional[int] = None
    image_approved: bool = False
