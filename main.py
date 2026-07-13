import os
import argparse
import asyncio
import logging
import uvicorn
from datetime import datetime
from fastapi import FastAPI

# App imports
from app.config import settings
from app.database import async_session_factory
from app.database.prompt_repository import PromptRepository
from app.services.prompt_service import PromptService
from google.adk.sessions import InMemorySessionService

# Configure logging using standard library logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("imgre_main")

# Instantiate FastAPI application
app = FastAPI(title=settings.PROJECT_NAME)

@app.get("/")
async def read_root():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "debug_mode": settings.DEBUG,
        "timestamp": datetime.now().isoformat()
    }

async def execute_prompt_loop():
    """Executes a single iteration of the Multi-Agent Prompt Optimization Loop."""
    logger.info("Initializing Imgre Prompt Optimization Loop...")

    # Generate unique session parameters
    session_id = f"daily-session-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}"
    user_id = "mvp_cli_operator"

    logger.info(f"User ID: {user_id} | Session ID: {session_id}")

    try:
        # Create asynchronous database session context
        async with async_session_factory() as db_session:
            # Instantiate Repositories and Services
            prompt_repo = PromptRepository(db_session)
            session_service = InMemorySessionService()
            prompt_service = PromptService(
                prompt_repository=prompt_repo,
                session_service=session_service,
                app_name="Imgre"
            )

            logger.info("Executing Prompt Optimization Workflow Service...")
            db_prompt = await prompt_service.run_prompt_optimization_workflow(
                user_id=user_id,
                session_id=session_id
            )

            print("\n" + "="*60)
            print("        PROMPT OPTIMIZATION LOOP EXECUTION SUCCESSFUL")
            print("="*60)
            print(f"Prompt Database ID : {db_prompt.id}")
            print(f"Title              : {db_prompt.title}")
            print(f"Status             : {db_prompt.status.upper()}")
            print(f"Attempts Run       : {db_prompt.attempts}")
            print(f"Aesthetic Score    : {db_prompt.aesthetic_score}/100.0")
            print(f"Psychology Score   : {db_prompt.psychology_score}/100.0")
            print("-"*60)
            print("Optimized Visual Prompt:")
            print(db_prompt.prompt)
            print("="*60 + "\n")

    except Exception as e:
        logger.error(f"Execution failed with error: {e}", exc_info=True)
        raise

def run_migrations():
    """Runs database migrations using Alembic."""
    import subprocess
    logger.info("Applying database migrations with Alembic...")
    try:
        result = subprocess.run(
            [".venv/bin/alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Migrations successfully applied.")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed with exit code {e.returncode}:")
        print(e.stderr)
        raise

def main():
    """Primary entry point for both web service and CLI runtime."""
    parser = argparse.ArgumentParser(
        description="Imgre Multi-Agent Automation System CLI"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--run",
        action="store_true",
        help="Run a single-pass of the multi-agent prompt optimization loop"
    )
    group.add_argument(
        "--migrate",
        action="store_true",
        help="Apply outstanding database migrations using Alembic"
    )
    group.add_argument(
        "--serve",
        action="store_true",
        help="Start the FastAPI web API server (Default behavior if no flag passed)"
    )

    args = parser.parse_args()

    if args.run:
        asyncio.run(execute_prompt_loop())
    elif args.migrate:
        run_migrations()
    else:
        # Default behavior: run web server
        logger.info(f"Starting {settings.PROJECT_NAME} Web Server...")
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)

if __name__ == "__main__":
    main()
