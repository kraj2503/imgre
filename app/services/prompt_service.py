from typing import List, Dict, Any, Optional
import logging

# ADK and GenAI imports
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.events import Event, EventActions
from google.genai.types import Content, Part

# Local codebase imports
from app.database.prompt_repository import PromptRepository
from app.models.prompt import Prompt
from app.agents.orchestrator import (
    trend_research_agent,
    prompt_generation_agent,
    prompt_review_subagent,
)

logger = logging.getLogger(__name__)


class PromptService:
    """Service to coordinate the multi-agent visual trend-to-prompt optimization loop

    and persist results to the database.
    """

    def __init__(
        self,
        prompt_repository: PromptRepository,
        session_service: BaseSessionService,
        app_name: str = "Imgre",
    ):
        """Initializes the PromptService.

        Args:
            prompt_repository: The async repository wrapper for SQL operations.
            session_service: The ADK Session Service for state and history management.
            app_name: The application name identifier for ADK sessions. Defaults to "Imgre".
        """
        self.prompt_repository = prompt_repository
        self.session_service = session_service
        self.app_name = app_name

    def _compile_feedback_history(self, feedback_history: List[Dict[str, Any]]) -> str:
        """Aggregates and formats prior feedback attempts for the generator agent.

        Args:
            feedback_history: The list of prior reviewer actions extracted from state.

        Returns:
            A compiled critique string targeting visual and psychological adjustments.
        """
        if not feedback_history:
            return ""

        compiled = (
            "Here is the critical critique feedback from previous attempts. "
            "You MUST address each of these points to refine and improve the scores:\n"
        )
        for idx, entry in enumerate(feedback_history, 1):
            reviewer = entry.get("reviewer", "Unknown Reviewer")
            score = entry.get("score", "N/A")
            approved = "Approved" if entry.get("approved") else "Rejected"
            feedback_raw = entry.get("feedback")

            if isinstance(feedback_raw, list):
                feedback_str = "\n".join(f"  - {item}" for item in feedback_raw)
            else:
                feedback_str = f"  - {feedback_raw}"

            compiled += f"\n[Review {idx}] {reviewer} (Score: {score}/100 - {approved}):\n{feedback_str}\n"

        return compiled

    async def run_prompt_optimization_workflow(
        self, user_id: str, session_id: str
    ) -> Prompt:
        """Coordinates the end-to-end trend gathering, prompt optimization loop, and database save.

        Args:
            user_id: The ID of the user requesting the workflow.
            session_id: The unique identifier for this daily execution session.

        Returns:
            The persisted Prompt database model record.
        """
        logger.info(f"Starting prompt optimization workflow for session {session_id}")

        # ----------------- Step 1: Ensure Session Exists -----------------
        session = await self.session_service.get_session(
            app_name=self.app_name, user_id=user_id, session_id=session_id
        )
        if session is None:
            session = await self.session_service.create_session(
                app_name=self.app_name, user_id=user_id, session_id=session_id
            )

        # ----------------- Step 2: Run Trend Research Agent -----------------
        logger.info("Executing Trend Research Agent...")
        trend_runner = Runner(
            app_name=self.app_name,
            agent=trend_research_agent,
            session_service=self.session_service,
            auto_create_session=True,
        )

        trend_query = Content(
            role="user",
            parts=[Part(text="Gather and analyze the latest visual art, fashion, and photography trends.")],
        )

        async for event in trend_runner.run_async(
            user_id=user_id, session_id=session_id, new_message=trend_query
        ):
            # Consume and log the agent event stream
            if event.content and event.content.parts:
                logger.debug(f"Trend Research Event: {event.content.parts[0].text}")

        # ----------------- Step 3: Run Prompt Optimization Loop -----------------
        max_attempts = 10
        attempt_count = 0
        approved = False
        aesthetic_score = 0.0
        psychology_score = 0.0

        while attempt_count < max_attempts:
            attempt_count += 1
            logger.info(f"--- Prompt Optimization Loop: Attempt {attempt_count}/{max_attempts} ---")

            # Re-fetch session to retrieve latest populated state
            session = await self.session_service.get_session(
                app_name=self.app_name, user_id=user_id, session_id=session_id
            )
            state = session.state if session else {}

            # Extract trend data and compile historical feedback
            trend_data = state.get("trend_summary", {})
            feedback_history = state.get("prompt_feedback_history", [])
            compiled_feedback = self._compile_feedback_history(feedback_history)

            # Formulate the instructional query for prompt generation
            gen_instruction = (
                f"Generate a highly descriptive image prompt optimized for modern generators based on the following trend summary:\n"
                f"{trend_data}\n\n"
            )
            if compiled_feedback:
                gen_instruction += (
                    f"Prior generation attempts did not meet our high-quality thresholds. "
                    f"Analyze and resolve the criticisms below in your new candidate:\n"
                    f"{compiled_feedback}\n"
                )

            # Execute Prompt Generation Agent
            logger.info("Invoking Prompt Generation Agent...")
            gen_runner = Runner(
                app_name=self.app_name,
                agent=prompt_generation_agent,
                session_service=self.session_service,
                auto_create_session=True,
            )
            gen_query = Content(
                role="user",
                parts=[Part(text=gen_instruction)],
            )

            async for event in gen_runner.run_async(
                user_id=user_id, session_id=session_id, new_message=gen_query
            ):
                pass

            # Re-fetch state to extract the newly generated candidate prompt details
            session = await self.session_service.get_session(
                app_name=self.app_name, user_id=user_id, session_id=session_id
            )
            state = session.state if session else {}
            candidate_title = state.get("prompt_candidate_title")
            candidate_text = state.get("prompt_candidate_text")

            # Execute Parallel Review Agent (prompt_review_subagent)
            logger.info("Invoking Parallel Review Agents...")
            review_instruction = (
                f"Evaluate the following visual prompt candidate against our targeted visual trends.\n\n"
                f"Candidate Title: {candidate_title}\n"
                f"Candidate Prompt: {candidate_text}\n\n"
                f"Target Visual Trends:\n{trend_data}\n"
            )

            review_runner = Runner(
                app_name=self.app_name,
                agent=prompt_review_subagent,
                session_service=self.session_service,
                auto_create_session=True,
            )
            review_query = Content(
                role="user",
                parts=[Part(text=review_instruction)],
            )

            async for event in review_runner.run_async(
                user_id=user_id, session_id=session_id, new_message=review_query
            ):
                pass

            # Retrieve scores from session state to check threshold exit conditions
            session = await self.session_service.get_session(
                app_name=self.app_name, user_id=user_id, session_id=session_id
            )
            state = session.state if session else {}
            aesthetic_score = state.get("aesthetic_score", 0.0)
            psychology_score = state.get("psychology_score", 0.0)

            logger.info(
                f"Attempt {attempt_count} results -> Aesthetic Score: {aesthetic_score}, "
                f"Psychology Score: {psychology_score}"
            )

            # Pass-criteria: Both scores must be >= 90
            if aesthetic_score >= 90.0 and psychology_score >= 90.0:
                logger.info("Prompt approved with perfect quality marks. Exiting loop.")
                approved = True
                break

            logger.info("Pass thresholds not met. Refining feedback for next attempt.")

        # ----------------- Step 4: Database Save & State Synchronization -----------------
        logger.info("Saving prompt optimization results to database...")

        # Reload session state to guarantee data consistency
        session = await self.session_service.get_session(
            app_name=self.app_name, user_id=user_id, session_id=session_id
        )
        state = session.state if session else {}

        final_title = state.get("prompt_candidate_title") or f"Automated Daily Prompt ({session_id})"
        final_prompt_text = state.get("prompt_candidate_text") or ""

        # Construct trend_summary JSON payload mapping raw trends & attempt logs
        trend_summary_payload = {
            "raw_trends": state.get("trend_summary"),
            "feedback_history": state.get("prompt_feedback_history", []),
        }

        # Persist utilizing PromptRepository async interface
        db_prompt = await self.prompt_repository.create(
            title=final_title,
            prompt=final_prompt_text,
            version=attempt_count,
            trend_summary=trend_summary_payload,
            aesthetic_score=aesthetic_score,
            psychology_score=psychology_score,
            attempts=attempt_count,
            status="approved" if approved else "rejected",
        )

        logger.info(
            f"Successfully persisted prompt database record. ID: {db_prompt.id}, "
            f"Status: {db_prompt.status}, Attempts Run: {db_prompt.attempts}"
        )

        # Synchronize database state back to the session state
        # This publishes the prompt ID and the approval flag to other downstream agents
        await self.session_service.append_event(
            session=session,
            event=Event(
                invocation_id="",
                author="system",
                actions=EventActions(
                    state_delta={
                        "prompt_id_saved": db_prompt.id,
                        "prompt_approved": approved,
                    }
                ),
            ),
        )

        return db_prompt
