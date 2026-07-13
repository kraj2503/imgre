Based on the current progress recorded in `CLAUDE.md` and the comprehensive technical blueprints outlined in `future.md`, **Milestones 1 through 5 are fully completed**, meaning the core visual research and prompt optimization MVP is ready and runnable. 

There are **3 major milestones remaining** to complete the full production pipeline:

---

### 1. Milestone 6: Image Generation, Ranking & Vision Review (Estimated 40% of remaining effort)
This milestone connects the approved prompts to visual output. The tasks left to implement are:
*   **State Additions**: Adding score and approval state fields to `AgentWorkflowState` in `app/agents/state.py`.
*   **Image Agent Instructions & Callbacks**: Writing the detailed prompt instructions, schemas, and callbacks for `Image_Ranking_Agent`, `Aesthetic_Image_Review_Agent`, and `Human_Appeal_Image_Review_Agent` inside `app/agents/orchestrator.py`.
*   **Image Service (`app/services/image_service.py`)**: Developing the domain service that:
    1.  Checks if $\ge 3$ approved prompts without images exist.
    2.  Invokes Google GenAI Imagen (`imagen-3.0-generate-002`) to render 5 variations (with a solid 1x1 PNG fallback).
    3.  Persists the variations in the database and saves files to disk.
    4.  Runs the ADK Ranking and Parallel Review agents (requiring raw multi-modal bytes passing).
    5.  Coordinates the 5x retry loop and handles the "highest-score fallback" if no variation scores $\ge 90$ on both reviews.

---

### 2. Milestone 7: Daily Scheduler & FastAPI Endpoints (Estimated 40% of remaining effort)
This milestone handles backend scheduling and exposes the system to the web:
*   **API Schemas (`app/schemas/api_schemas.py`)**: Defining response structures for Prompts, Images, and System Metrics.
*   **APScheduler Daemon (`app/scheduler/scheduler.py`)**: Building the daily scheduler cron job set to execute at 09:00 AM local time.
*   **API Routers (`app/api/endpoints/`)**: Implementing REST controllers:
    *   `prompts.py`: Paginated lists and detailed views.
    *   `images.py`: Image asset lookups.
    *   `triggers.py`: Manual endpoints to force-run the prompt loop, image pipeline, or combined daily run.
    *   `system.py`: Real-time system metrics (total counts, average reviewer scores).
    *   `api.py`: Core routing registry.

---

### 3. Milestone 8: Finalize Web Lifecycle & CLI Arguments (Estimated 20% of remaining effort)
This final step binds all CLI features and handles file-serving:
*   **Lifespan Management**: Updating `main.py` to start and gracefully stop the APScheduler background thread inside FastAPI's async lifespan context.
*   **Static Directory Mounting**: Configuring FastAPI to mount and serve the generated PNG files under `/static/images`.
*   **CLI Expansion**: Adding `--run-image` and `--run-daily` options to the parser in `main.py` so operators can trigger any subset of the pipeline manually.