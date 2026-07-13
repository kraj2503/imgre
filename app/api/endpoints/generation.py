import os
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.database.prompt_repository import PromptRepository
from app.database.image_repository import ImageRepository
from app.services.prompt_service import PromptService
from app.services.image_service import ImageService
from app.schemas.api_schemas import ArtGenerationRequest, ArtGenerationResponse, PromptResponse, ImageResponse
from google.adk.sessions import InMemorySessionService

logger = logging.getLogger(__name__)
router = APIRouter()

# Global session service to maintain session history across consecutive API calls
session_service = InMemorySessionService()

@router.post("/generate-art", response_model=ArtGenerationResponse)
async def generate_optimized_art(
    request: ArtGenerationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Triggers the trend research, prompt optimization loop, and image generation/ranking pipeline.

    Users can supply an initial starting creative 'user_idea' or provide refining
    'user_edits' to alter previous runs under the same session ID.
    """
    session_id = request.session_id or f"api-session-{uuid.uuid4().hex[:12]}"
    user_id = "api_ui_operator"

    logger.info(f"Triggering interactive art generation: Session={session_id}, User={user_id}")

    # 1. Initialize repos and services
    prompt_repo = PromptRepository(db)
    image_repo = ImageRepository(db)

    prompt_service = PromptService(
        prompt_repository=prompt_repo,
        session_service=session_service,
        app_name="Imgre"
    )

    image_service = ImageService(
        prompt_repository=prompt_repo,
        image_repository=image_repo,
        session_service=session_service,
        app_name="Imgre"
    )

    try:
        # 2. Run prompt optimization loop (incorporating user starting idea and direct edits)
        logger.info("Executing prompt loop service...")
        db_prompt = await prompt_service.run_prompt_optimization_workflow(
            user_id=user_id,
            session_id=session_id,
            user_idea=request.user_idea,
            user_edits=request.user_edits
        )

        # 3. Run image variations generation, ranking, and dual quality reviews
        logger.info(f"Executing image loop service for prompt ID {db_prompt.id}...")
        image_ids = await image_service.run_image_pipeline_for_prompt(
            user_id=user_id,
            session_id=session_id,
            prompt_id=db_prompt.id
        )

        # 4. Fetch created records to build the final API response
        images = await image_repo.get_by_prompt_id(db_prompt.id)

        best_image_id = None
        best_image_url = None

        # Identify the selected 'is_best' variation
        for img in images:
            if img.is_best:
                best_image_id = img.id
                # Map the local file path to a static web server asset URL path
                base_name = os.path.basename(img.file_path)
                best_image_url = f"/static/images/{base_name}"
                break

        # 5. Build response schemas
        prompt_response = PromptResponse.from_orm(db_prompt)
        images_response = [ImageResponse.from_orm(img) for img in images]

        return ArtGenerationResponse(
            prompt=prompt_response,
            images=images_response,
            best_image_id=best_image_id,
            best_image_url=best_image_url
        )

    except Exception as e:
        logger.error(f"Art generation pipeline failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during multi-agent art generation: {str(e)}"
        )
