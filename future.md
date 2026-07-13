# Future Improvements Roadmap (Milestones 6 - 8)

This document outlines the step-by-step implementation guide, design specifications, and code blueprints for transitioning the **Imgre Multi-Agent Art Optimization System** from the current MVP to a production-grade automated pipeline. Address this document directly to the implementing agent (such as Claude Opus) as clear, executable commands.

---

## Milestone 6: Image Generation, Ranking & Vision Review

Implement the downstream image automation pipeline. This pipeline executes when **$\ge 3$ approved prompts** without existing images are found in the database.

### 1. Update Session State Schema
**File to modify**: `app/agents/state.py`
Add fields to `AgentWorkflowState` to store parallel reviewer scores and the final approval result:
```python
    # Image Pipeline State Additions
    aesthetic_image_score: float = 0.0
    aesthetic_image_approved: bool = False
    human_appeal_image_score: float = 0.0
    human_appeal_image_approved: bool = False
```

### 2. Implement Image Agent Skeletons & Callbacks
**File to modify**: `app/agents/orchestrator.py`
1. Define the following callbacks to unpack agent JSON results and commit them to the ADK context state:
```python
from app.schemas.agent_schemas import (
    TrendAnalysisOutput,
    PromptGenerationOutput,
    ReviewOutput,
    RankingOutput
)

async def image_ranking_after_callback(ctx):
    """Unpacks the image ranking output and sets selected_best_image_id in state."""
    ranking_data = ctx.state.get("temp:image_ranking")
    if ranking_data:
        ctx.state["selected_best_image_id"] = ranking_data.get("selected_image_id")

async def aesthetic_image_review_after_callback(ctx):
    """Logs aesthetic image review results."""
    review = ctx.state.get("temp:aesthetic_image_review")
    if review:
        ctx.state["aesthetic_image_score"] = float(review.get("score", 0.0))
        ctx.state["aesthetic_image_approved"] = bool(review.get("approved", False))

async def human_appeal_image_review_after_callback(ctx):
    """Logs human appeal image review results."""
    review = ctx.state.get("temp:human_appeal_image_review")
    if review:
        ctx.state["human_appeal_image_score"] = float(review.get("score", 0.0))
        ctx.state["human_appeal_image_approved"] = bool(review.get("approved", False))

async def image_review_parallel_after_callback(ctx):
    """Executes after both parallel image reviews complete, calculating joint pipeline approval."""
    aes_approved = ctx.state.get("aesthetic_image_approved", False)
    human_approved = ctx.state.get("human_appeal_image_approved", False)
    ctx.state["image_approved"] = aes_approved and human_approved
```

2. Replace the empty skeleton definitions with production prompts and schema mapping:
```python
# 5. Image Ranking Agent
image_ranking_agent = BaseAppAgent(
    name="Image_Ranking_Agent",
    description="Selects the highest quality and most faithful image variation from the generated choices.",
    static_instruction="""
    You are a master Creative Director and visual art ranking expert.
    Your task is to review 5 image variations generated for a given prompt and select the absolute best execution based on:
    - Faithfulness to the original detailed prompt text.
    - Detail level, rendering clarity, and high photographic quality.
    - Composition, focal point, and absence of obvious rendering glitch patterns.
    - Harmonious lighting and colors.

    You will be provided with multiple images alongside their Database IDs. Identify each image by its ID.
    You must output:
    1. The selected image ID (an integer corresponding to the ID given for the best image).
    2. An ordered list of all the image IDs, ranked from best to worst.

    Structure your response strictly matching the RankingOutput schema. Do not output anything outside the JSON.
    """,
    output_schema=RankingOutput,
    output_key="temp:image_ranking",
    after_agent_callback=image_ranking_after_callback
)

# 6. Image Review Agents (Parallel Execution)
aesthetic_image_review_agent = BaseAppAgent(
    name="Aesthetic_Image_Review_Agent",
    description="Verifies the chosen image for rendering artifacts, technical flaws, and anatomic issues.",
    static_instruction="""
    You are an elite Visual Quality Assurance Engineer.
    Your task is to analyze the selected best image for rendering artifacts, technical flaws, and anatomical issues.
    Specifically evaluate:
    - Textures and fine details (look for noise, blurriness, or blocky artifacts).
    - Geometry and anatomy (look for extra limbs, warped features, or nonsensical structural connections).
    - Lighting and shadow consistency (ensure shadows fall realistically and light sources are consistent).

    Provide:
    1. A score from 0 to 100 based on aesthetic and technical execution.
    2. A boolean approval (True if score is 90 or above, otherwise False).
    3. A list of constructive visual critiques and details of any artifacts.

    Structure your response strictly matching the ReviewOutput schema. Do not output anything outside the JSON.
    """,
    output_schema=ReviewOutput,
    output_key="temp:aesthetic_image_review",
    after_agent_callback=aesthetic_image_review_after_callback
)

human_appeal_image_review_agent = BaseAppAgent(
    name="Human_Appeal_Image_Review_Agent",
    description="Verifies the chosen image for raw beauty, comfort, luxury, and consumer engagement.",
    static_instruction="""
    You are an expert Content Director and Human Psychology Reviewer.
    Your task is to evaluate the selected image for raw visual beauty, emotional resonance, luxury, comfort, and general consumer engagement.
    Specifically evaluate:
    - Emotional resonance (does the image evoke a strong, positive, or compelling human emotion?).
    - Visual beauty and comfort (is the image inviting, aesthetically pleasant, and satisfying to view?).
    - Luxury and elegance (does it convey premium quality or high production value?).
    - Concept uniqueness (does the scene stand out and capture attention?).

    Provide:
    1. A score from 0 to 100 based on human appeal and engagement.
    2. A boolean approval (True if score is 90 or above, otherwise False).
    3. A list of emotional and psychological critiques.

    Structure your response strictly matching the ReviewOutput schema. Do not output anything outside the JSON.
    """,
    output_schema=ReviewOutput,
    output_key="temp:human_appeal_image_review",
    after_agent_callback=human_appeal_image_review_after_callback
)

image_review_subagent = ParallelAgent(
    name="Image_Review_Subagent",
    sub_agents=[aesthetic_image_review_agent, human_appeal_image_review_agent],
    after_agent_callback=image_review_parallel_after_callback
)
```

### 3. Create the Image Service
**File to create**: `app/services/image_service.py`
Build a core workflow domain service coordinating the generation and evaluation steps. Use the Google GenAI SDK to call the Imagen model (`imagen-3.0-generate-002`) and local file storage. Implement raw image bytes passing for multimodal evaluation inside ADK runners.

```python
import os
import logging
import base64
from typing import List, Dict, Any
from google import genai
from google.genai.types import Content, Part, GenerateImagesConfig
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.database.prompt_repository import PromptRepository
from app.database.image_repository import ImageRepository

logger = logging.getLogger(__name__)

class ImageService:
    """Service to coordinate visual generation, ranking and review workflows."""

    def __init__(
        self,
        prompt_repository: PromptRepository,
        image_repository: ImageRepository,
        session_service: BaseSessionService,
        app_name: str = "Imgre"
    ):
        self.prompt_repository = prompt_repository
        self.image_repository = image_repository
        self.session_service = session_service
        self.app_name = app_name
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def generate_images_with_fallback(self, prompt_text: str) -> List[bytes]:
        """Calls Google GenAI Imagen with retry and mock fallback if it fails."""
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is not configured. Falling back to mock image generation.")
            return [self._get_mock_image_bytes(i) for i in range(5)]

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True
        )
        def call_imagen():
            config = GenerateImagesConfig(
                number_of_images=5,
                output_mime_type="image/png",
                aspect_ratio="1:1",
                person_generation="ALLOW_ADULT",
            )
            return self.client.models.generate_images(
                model=settings.IMAGEN_MODEL,
                prompt=prompt_text,
                config=config
            )

        try:
            response = call_imagen()
            images_bytes = []
            for gen_img in response.generated_images:
                if gen_img.image and gen_img.image.image_bytes:
                    images_bytes.append(gen_img.image.image_bytes)
            
            if len(images_bytes) < 5:
                logger.warning(f"Imagen returned only {len(images_bytes)} images. Filling with mock images.")
                while len(images_bytes) < 5:
                    images_bytes.append(self._get_mock_image_bytes(len(images_bytes)))
            return images_bytes
        except Exception as e:
            logger.error(f"Imagen API failed completely: {e}. Falling back to mock images.")
            return [self._get_mock_image_bytes(i) for i in range(5)]

    def _get_mock_image_bytes(self, index: int) -> bytes:
        """Returns a valid minimal 1x1 solid-color PNG as fallback bytes."""
        # Standard 1x1 solid base64 PNG
        mock_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        return base64.b64decode(mock_png)

    async def run_image_pipeline(self, user_id: str, session_id: str) -> List[int]:
        """Retrieves approved prompts without images, runs image generation,

        ranking, and review workflows for each prompt up to 5 retry attempts.
        """
        logger.info("Executing Image Generation & Review pipeline...")

        # Step 1: Verify pre-requisite: we need at least 3 approved prompts lacking images
        approved_prompts = await self.prompt_repository.get_approved_prompts_without_images()
        if len(approved_prompts) < 3:
            logger.warning(
                f"Fewer than 3 approved prompts without images exist (found {len(approved_prompts)}). "
                "Skipping image generation as per requirements."
            )
            return []

        processed_prompt_ids = []

        # Step 2: Loop through each approved prompt lacking images
        for prompt in approved_prompts:
            logger.info(f"Processing approved prompt ID {prompt.id}: {prompt.title}")
            success = False
            best_overall_image_id = None
            best_overall_score = -1.0

            # Import agents inside the method to avoid circular import issues
            from app.agents.orchestrator import image_ranking_agent, image_review_subagent

            for attempt in range(1, 6):
                logger.info(f"--- Image pipeline attempt {attempt}/5 for Prompt ID {prompt.id} ---")

                # A. Generate 5 variations
                images_bytes = await self.generate_images_with_fallback(prompt.prompt)

                # B. Save to disk and create pending DB records
                db_images = []
                os.makedirs("static/images", exist_ok=True)
                for idx, img_bytes in enumerate(images_bytes):
                    file_name = f"prompt_{prompt.id}_attempt_{attempt}_var_{idx}.png"
                    file_path = os.path.join("static", "images", file_name)
                    with open(file_path, "wb") as f:
                        f.write(img_bytes)

                    db_img = await self.image_repository.create(
                        prompt_id=prompt.id,
                        file_path=file_path,
                        status="pending",
                        is_best=False,
                        metadata={"attempt": attempt, "variation": idx}
                    )
                    db_images.append(db_img)

                # C. Call Image Ranking Agent via Runner
                logger.info("Running Image Ranking Agent...")
                parts = [
                    Part.from_text(
                        text="Compare the following 5 generated image variations for the prompt and rank them. "
                        "Select the best execution. Here is the original prompt: "
                        f"'{prompt.prompt}'\n\n"
                    )
                ]
                for db_img in db_images:
                    with open(db_img.file_path, "rb") as f:
                        img_bytes = f.read()
                    parts.append(Part.from_text(text=f"Variation Database ID: {db_img.id}\n"))
                    parts.append(Part.from_bytes(data=img_bytes, mime_type="image/png"))
                    parts.append(Part.from_text(text="\n\n"))

                parts.append(Part.from_text(text="Please output your selection and complete ranking strictly in JSON format matching the schema."))
                ranking_query = Content(role="user", parts=parts)

                ranking_runner = Runner(
                    app_name=self.app_name,
                    agent=image_ranking_agent,
                    session_service=self.session_service,
                    auto_create_session=True,
                )

                async for event in ranking_runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=ranking_query
                ):
                    pass

                # Retrieve selected best image ID from state
                session = await self.session_service.get_session(
                    app_name=self.app_name, user_id=user_id, session_id=session_id
                )
                state = session.state if session else {}
                selected_best_id = state.get("selected_best_image_id")

                if not selected_best_id:
                    selected_best_id = db_images[0].id
                    logger.warning(f"Ranking agent failed to set selected_best_image_id. Using fallback image ID {selected_best_id}.")

                logger.info(f"Selected best image variation ID: {selected_best_id}")

                # D. Call parallel image review subagent for the chosen image
                logger.info("Running Image Review Agents...")
                chosen_img_record = next((img for img in db_images if img.id == selected_best_id), None)
                if not chosen_img_record:
                    chosen_img_record = await self.image_repository.get_by_id(selected_best_id)

                with open(chosen_img_record.file_path, "rb") as f:
                    chosen_bytes = f.read()

                review_parts = [
                    Part.from_text(
                        text="Evaluate the following selected image variation against visual quality, anatomical correctness, "
                        "aesthetic rendering, and emotional human appeal. "
                        f"Original Prompt: '{prompt.prompt}'\n\n"
                    ),
                    Part.from_bytes(data=chosen_bytes, mime_type="image/png"),
                    Part.from_text(text="\n\nProvide scores out of 100 and indicate approvals. Respond strictly using the JSON output schema.")
                ]
                review_query = Content(role="user", parts=review_parts)

                review_runner = Runner(
                    app_name=self.app_name,
                    agent=image_review_subagent,
                    session_service=self.session_service,
                    auto_create_session=True,
                )

                async for event in review_runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=review_query
                ):
                    pass

                # Retrieve scores from state
                session = await self.session_service.get_session(
                    app_name=self.app_name, user_id=user_id, session_id=session_id
                )
                state = session.state if session else {}
                aes_score = state.get("aesthetic_image_score", 0.0)
                human_score = state.get("human_appeal_image_score", 0.0)
                avg_score = (aes_score + human_score) / 2.0

                logger.info(
                    f"Evaluation Results -> Aesthetic Score: {aes_score}, "
                    f"Human Appeal Score: {human_score}, Combined Average: {avg_score}"
                )

                if avg_score > best_overall_score:
                    best_overall_score = avg_score
                    best_overall_image_id = selected_best_id

                # Pass criteria: Both scores >= 90
                if aes_score >= 90.0 and human_score >= 90.0:
                    logger.info(f"Image approved with scores {aes_score} & {human_score}. Setting as best image.")
                    await self.image_repository.update(selected_best_id, {"status": "approved", "score": avg_score})
                    await self.image_repository.set_best_image(selected_best_id)

                    for db_img in db_images:
                        if db_img.id != selected_best_id:
                            await self.image_repository.update(db_img.id, {"status": "rejected"})

                    success = True
                    break
                else:
                    logger.info("Scores did not meet criteria (>= 90). Marking this attempt variations as failed_review.")
                    for db_img in db_images:
                        await self.image_repository.update(db_img.id, {"status": "failed_review"})

            if not success and best_overall_image_id:
                logger.warning(
                    f"No image attempt scored >= 90 after 5 tries for Prompt ID {prompt.id}. "
                    f"Falling back to highest scoring image (ID: {best_overall_image_id}, Score: {best_overall_score})."
                )
                await self.image_repository.update(best_overall_image_id, {"status": "approved", "score": best_overall_score})
                await self.image_repository.set_best_image(best_overall_image_id)

            processed_prompt_ids.append(prompt.id)

        return processed_prompt_ids
```

---

## Milestone 7: Daily Scheduler & FastAPI Endpoints

### 1. Create API Response/Request Schemas
**File to create**: `app/schemas/api_schemas.py`
Define Pydantic structures modeling API transfers:
```python
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class ImageResponse(BaseModel):
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
    images: List[ImageResponse] = []

class SystemMetricsResponse(BaseModel):
    total_prompts: int
    approved_prompts: int
    rejected_prompts: int
    pending_prompts: int
    total_images: int
    approved_images: int
    rejected_images: int
    average_aesthetic_score: float
    average_psychology_score: float
    average_image_score: float
```

### 2. Create Background Scheduler Service
**File to create**: `app/scheduler/scheduler.py`
Configure the standard python `apscheduler` package to run as an async daemon inside our lifespan loop:
```python
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import async_session_factory
from app.database.prompt_repository import PromptRepository
from app.database.image_repository import ImageRepository
from app.services.prompt_service import PromptService
from app.services.image_service import ImageService
from google.adk.sessions import InMemorySessionService

logger = logging.getLogger(__name__)

session_service = InMemorySessionService()
scheduler = AsyncIOScheduler()

async def run_daily_combined_workflow():
    """Runs the end-to-end daily art-to-image workflow."""
    logger.info("Executing scheduled daily automated workflow...")
    session_id = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    user_id = "scheduler_daemon"

    async with async_session_factory() as session:
        prompt_repo = PromptRepository(session)
        image_repo = ImageRepository(session)

        # A. Run Prompt optimization loop
        prompt_service = PromptService(prompt_repo, session_service)
        try:
            approved_prompt = await prompt_service.run_prompt_optimization_workflow(user_id, session_id)
            logger.info(f"Scheduled prompt workflow finished. Status: {approved_prompt.status}")
        except Exception as e:
            logger.error(f"Error during scheduled prompt optimization: {e}", exc_info=True)
            return

        # B. Run Image pipeline
        image_service = ImageService(prompt_repo, image_repo, session_service)
        try:
            processed_prompts = await image_service.run_image_pipeline(user_id, session_id)
            logger.info(f"Scheduled image pipeline finished. Processed Prompts: {processed_prompts}")
        except Exception as e:
            logger.error(f"Error during scheduled image pipeline: {e}", exc_info=True)

def start_scheduler():
    logger.info(f"Starting APScheduler daily daemon at {settings.SCHEDULER_CRON_HOUR:02d}:{settings.SCHEDULER_CRON_MINUTE:02d} local...")
    scheduler.add_job(
        run_daily_combined_workflow,
        trigger=CronTrigger(
            hour=settings.SCHEDULER_CRON_HOUR,
            minute=settings.SCHEDULER_CRON_MINUTE
        ),
        id="daily_combined_workflow",
        replace_existing=True
    )
    scheduler.start()

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler daily daemon stopped successfully.")
```

### 3. Create Controllers and Endpoints
**Files to create**: Under `app/api/endpoints/`
1. **`app/api/endpoints/prompts.py`**:
```python
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
    repo = PromptRepository(db)
    return await repo.get_all(skip=skip, limit=limit, status=status)

@router.get("/{prompt_id}", response_model=PromptDetailResponse)
async def get_prompt(prompt_id: int, db: AsyncSession = Depends(get_db)):
    repo = PromptRepository(db)
    prompt = await repo.get_by_id(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt
```

2. **`app/api/endpoints/images.py`**:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.database.image_repository import ImageRepository
from app.schemas.api_schemas import ImageResponse

router = APIRouter()

@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(image_id: int, db: AsyncSession = Depends(get_db)):
    repo = ImageRepository(db)
    image = await repo.get_by_id(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return image

@router.get("/prompt/{prompt_id}", response_model=List[ImageResponse])
async def list_images_by_prompt(prompt_id: int, db: AsyncSession = Depends(get_db)):
    repo = ImageRepository(db)
    return await repo.get_by_prompt_id(prompt_id)
```

3. **`app/api/endpoints/triggers.py`**:
```python
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.database import get_db, async_session_factory
from app.database.prompt_repository import PromptRepository
from app.database.image_repository import ImageRepository
from app.services.prompt_service import PromptService
from app.services.image_service import ImageService
from app.scheduler.scheduler import run_daily_combined_workflow, session_service
from app.schemas.api_schemas import PromptResponse

router = APIRouter()

@router.post("/prompt", response_model=PromptResponse)
async def trigger_prompt_workflow(db: AsyncSession = Depends(get_db)):
    session_id = f"manual-prompt-{int(datetime.utcnow().timestamp())}"
    user_id = "manual_operator"
    repo = PromptRepository(db)
    service = PromptService(repo, session_service)
    try:
        return await service.run_prompt_optimization_workflow(user_id, session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run prompt loop: {str(e)}")

@router.post("/image")
async def trigger_image_workflow(background_tasks: BackgroundTasks):
    session_id = f"manual-image-{int(datetime.utcnow().timestamp())}"
    user_id = "manual_operator"

    async def run_pipeline():
        async with async_session_factory() as session:
            prompt_repo = PromptRepository(session)
            image_repo = ImageRepository(session)
            service = ImageService(prompt_repo, image_repo, session_service)
            await service.run_image_pipeline(user_id, session_id)

    background_tasks.add_task(run_pipeline)
    return {"message": "Image generation and evaluation pipeline started in background", "session_id": session_id}

@router.post("/daily")
async def trigger_daily_workflow(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_daily_combined_workflow)
    return {"message": "Scheduled daily combined workflow triggered immediately in background"}
```

4. **`app/api/endpoints/system.py`**:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.prompt import Prompt
from app.models.image import Image
from app.schemas.api_schemas import SystemMetricsResponse

router = APIRouter()

@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(db: AsyncSession = Depends(get_db)):
    total_p = await db.scalar(select(func.count(Prompt.id)))
    approved_p = await db.scalar(select(func.count(Prompt.id)).filter(Prompt.status == "approved"))
    rejected_p = await db.scalar(select(func.count(Prompt.id)).filter(Prompt.status == "rejected"))
    pending_p = await db.scalar(select(func.count(Prompt.id)).filter(Prompt.status == "pending"))

    total_i = await db.scalar(select(func.count(Image.id)))
    approved_i = await db.scalar(select(func.count(Image.id)).filter(Image.status == "approved"))
    rejected_i = await db.scalar(select(func.count(Image.id)).filter(Image.status == "rejected"))

    avg_aes_p = await db.scalar(select(func.avg(Prompt.aesthetic_score))) or 0.0
    avg_psych_p = await db.scalar(select(func.avg(Prompt.psychology_score))) or 0.0
    avg_img_score = await db.scalar(select(func.avg(Image.score))) or 0.0

    return SystemMetricsResponse(
        total_prompts=total_p,
        approved_prompts=approved_p,
        rejected_prompts=rejected_p,
        pending_prompts=pending_p,
        total_images=total_i,
        approved_images=approved_i,
        rejected_images=rejected_i,
        average_aesthetic_score=round(float(avg_aes_p or 0.0), 2),
        average_psychology_score=round(float(avg_psych_p or 0.0), 2),
        average_image_score=round(float(avg_img_score or 0.0), 2),
    )
```

5. **`app/api/api.py`** (Register API Router):
```python
from fastapi import APIRouter
from app.api.endpoints import prompts, images, triggers, system

api_router = APIRouter()
api_router.include_router(prompts.router, prefix="/prompts", tags=["prompts"])
api_router.include_router(images.router, prefix="/images", tags=["images"])
api_router.include_router(triggers.router, prefix="/trigger", tags=["triggers"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
```

---

## Milestone 8: Finalize Web lifecycle and CLI Arguments

### 1. Incorporate Lifespan, Directory Mounting, and CLI flags
**File to modify**: `main.py`
Incorporate Lifespan triggers to start/stop the Scheduler daemon and parse CLI flags:
```python
import os
import argparse
import asyncio
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api.api import api_router
from app.scheduler.scheduler import start_scheduler, stop_scheduler

# Lifecycle Management for APScheduler inside FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start scheduler
    start_scheduler()
    yield
    # Shutdown: Stop scheduler
    stop_scheduler()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Mount directory to serve generated image files
os.makedirs("static/images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# ... (Insert previous CLI Runners for prompt and image loops) ...
```

---

## Verification and Run Manual

Execute these steps on the completed codebase:

1. **Verify Python Compilations**:
```bash
.venv/bin/python -m py_compile main.py app/**/*.py
```

2. **Triggering CLI executions**:
- Run Prompt optimization loop:
  ```bash
  .venv/bin/python main.py --run
  ```
- Apply pending Alembic Migrations:
  ```bash
  .venv/bin/python main.py --migrate
  ```
- Run Web server:
  ```bash
  .venv/bin/python main.py --serve
  ```
