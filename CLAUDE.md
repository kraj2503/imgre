# CLAUDE.md — Imgre Multi-Agent Automation Developer Guide

This file outlines the architecture, technology stack, setup commands, and development guidelines for the **Imgre Multi-Agent Automation System**.

## System Architecture & Tech Stack

This project is built following **Clean Architecture** principles to coordinate a production-grade autonomous Multi-Agent AI system:
- **Core Orchestrator**: Google Agent Development Kit (Google ADK) 2.4.0 & Google GenAI 2.11.0 (with Gemini 2.5 Flash)
- **Backend API & Scheduling**: FastAPI, Uvicorn, and APScheduler (future task)
- **Database & Persistence**: PostgreSQL 16 (with asyncpg driver), SQLAlchemy 2.0 (async mapping & declarative base), and Alembic for async migrations.
- **Log Management**: Standard Logging (structured output)
- **Environment & Dependency Manager**: `uv` package manager and Pydantic Settings V2.

---

## Directory Layout

```
imgre/
├── app/                        # Main application package
│   ├── agents/                 # Google ADK agent personas & shared Pydantic states
│   ├── api/                    # FastAPI routes, schemas, and endpoints (future task)
│   ├── database/               # Database connection and async repository classes
│   ├── models/                 # SQLAlchemy 2.0 declarative database models
│   ├── scheduler/              # APScheduler daily orchestration setup (future task)
│   ├── services/               # Procedural service layer (loops, retries, DB transactions)
│   ├── utils/                  # Helper utilities and custom logger settings
│   ├── workflows/              # Google ADK custom workflow definitions
│   └── tests/                  # Integration and unit test suites
├── alembic/                    # Alembic migration scripts and configurations
├── .env                        # Local environment variables
├── .env.example                # Example environment variable template
├── Dockerfile                  # Lightweight Python 3.11 build container
├── docker-compose.yml          # FastAPI + PostgreSQL 16 container configurations
├── pyproject.toml              # Project metadata & package dependencies
├── future.md                   # Blueprint guide for Milestones 6 - 8
└── main.py                     # Primary entrypoint for both Web server and CLI runtimes
```

---

## Developer Commands

### Environment Setup & Synced Packages
Verify that python dependencies are synchronized using `uv`:
```bash
uv sync
```

### Module Compilations & Reference Verification
Compile all application files to verify syntax and references:
```bash
.venv/bin/python -m py_compile main.py app/database.py app/models/*.py app/database/*_repository.py app/agents/*.py app/schemas/*.py app/services/*.py alembic/versions/*.py
```

### Database Container Controls
Launch the local PostgreSQL 16 container:
```bash
docker compose up -d db
```

Check the status and health of the database container:
```bash
docker ps --filter name=imgre_db
```

### Alembic Migrations
To apply all pending database migrations against the active database:
```bash
.venv/bin/python main.py --migrate
```
Or use the standard command:
```bash
.venv/bin/alembic upgrade head
```

### Running the MVP Prompt Loop
To trigger a single-pass of the Multi-Agent Prompt Optimization Loop (Trend Analyst -> 10x loop -> parallel review critiques -> PostgreSQL save):
```bash
.venv/bin/python main.py --run
```

### Running the Web Server
To start the FastAPI web application and serve requests:
```bash
.venv/bin/python main.py --serve
```

---

## Implementation Progress

- **Milestone 1: Project Scaffolding & Configuration** — Completed. Clean Architecture directories, `.env`, Pydantic config settings, `Dockerfile`, `docker-compose.yml`, and `uv` dependencies fully established.
- **Milestone 2: Database & Repository Layer** — Completed. Modern SQLAlchemy 2.0 async connection, `Prompt` and `Image` relational schemas, decoupled async CRUD `PromptRepository` and `ImageRepository` classes, and Alembic async migration scripts fully completed.
- **Milestone 3: Google ADK Framework & Base Structures** — Completed. Established `BaseAppAgent` wrapper, structured Pydantic input/output schemas, delta-aware `AgentWorkflowState` model, and fully integrated the `root_agent` Sequential/Parallel orchestrator tree.
- **Milestone 4: Prompt Engineering Agents** — Completed. Implemented the Trend Research Agent (Visual Trend Analyst with `google_search` tool), Prompt Generation Agent (Elite Prompt Engineer), Aesthetic Review Agent (Visual Art Director), and Psychology Review Agent (Media Psychologist), fully integrated with output schemas and async state delta callbacks.
- **Milestone 5: Prompt Optimization Loop (MVP)** — Completed. Built `PromptService` executing the recursive 10x generation loop, historical critique aggregator feedback loop, visual review checks (aesthetic/psychology scores >= 90), async PostgreSQL persistence, and state delta updates. Combined it with a robust CLI runner in `main.py`.
- **Milestone 6: Image Generation, Ranking & Review** — Documented in `future.md`. Ready for future implementation.
- **Milestone 7: Daily Scheduler & FastAPI Endpoints** — Documented in `future.md`. Ready for future implementation.
- **Milestone 8: Finalize Web Lifecycle** — Documented in `future.md`. Ready for future implementation.

---

## Development Guidelines

- **Clean Architecture**: Never import database sessions or models directly inside your LLM agents. Keep agents lightweight and focused on text/vision inputs and outputs. Let the services layer (`app/services/`) govern loops, retries, and database transactions.
- **Async Execution**: Ensure all network IO, database operations, and API calls use asynchronous `async/await` syntax.
- **Pydantic V2**: Enforce strong types for agent configurations, state contexts, and API schemas.
- **Explicit Relationships**: When mapping image variation records, map python's attribute to `meta_data` (`mapped_column("metadata", JSON)`) to prevent naming conflicts with standard `Base.metadata`.
