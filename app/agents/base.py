from typing import List, Callable, Any, Optional
from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from app.config import settings
from app.agents.state import AgentWorkflowState

class BaseAppAgent(LlmAgent):
    """Custom Base Agent class extending google.adk.agents.LlmAgent.

    Ensures that our shared Pydantic session state is attached and validated,
    and applies our standard Gemini model and credentials from settings.
    """
    def __init__(
        self,
        name: str,
        description: str = "",
        instruction: Optional[str] = None,
        static_instruction: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        **kwargs
    ):
        # Configure model from settings
        model = kwargs.pop("model", Gemini(model=settings.DEFAULT_GEMINI_MODEL))

        # Enforce our shared session state schema for automatic delta-state validation
        state_schema = kwargs.pop("state_schema", AgentWorkflowState)

        super().__init__(
            name=name,
            description=description,
            model=model,
            instruction=instruction or "",
            static_instruction=static_instruction,
            state_schema=state_schema,
            tools=tools or [],
            **kwargs
        )
