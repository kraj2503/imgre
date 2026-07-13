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

    async def run_image_pipeline_for_prompt(self, user_id: str, session_id: str, prompt_id: int) -> List[int]:
        """Runs the image generation, ranking, and review workflow for a specific prompt ID."""
        logger.info(f"Starting image pipeline for Prompt ID {prompt_id}...")
        prompt = await self.prompt_repository.get_by_id(prompt_id)
        if not prompt:
            logger.error(f"Prompt ID {prompt_id} not found in database.")
            return []

        # Import agents inside the method to avoid circular import issues
        from app.agents.orchestrator import image_ranking_agent, image_review_subagent

        success = False
        best_overall_image_id = None
        best_overall_score = -1.0
        db_images = []

        # We execute up to 5 attempts to hit our high quality threshold (average review score >= 90)
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
                try:
                    with open(db_img.file_path, "rb") as f:
                        img_bytes = f.read()
                    parts.append(Part.from_text(text=f"Variation Database ID: {db_img.id}\n"))
                    parts.append(Part.from_bytes(data=img_bytes, mime_type="image/png"))
                    parts.append(Part.from_text(text="\n\n"))
                except Exception as e:
                    logger.error(f"Failed to read image file {db_img.file_path}: {e}")

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

            try:
                with open(chosen_img_record.file_path, "rb") as f:
                    chosen_bytes = f.read()
            except Exception as e:
                logger.error(f"Failed to read chosen image file: {e}")
                chosen_bytes = self._get_mock_image_bytes(0)

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

        return [img.id for img in db_images]
