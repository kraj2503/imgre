# Use a lightweight official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV WORKDIR=/workspace

# Set working directory
WORKDIR ${WORKDIR}

# Install basic system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer and resolver)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin/:${PATH}"

# Copy configuration files for dependency resolution
COPY pyproject.toml uv.lock ./

# Sync dependencies using uv (creates .venv in workspace)
RUN uv sync --frozen --no-dev

# Copy application source code
COPY app/ ./app/
COPY main.py ./

# Expose FastAPI default port
EXPOSE 8000

# Set environment path to use the uv-created virtual environment
ENV PATH="${WORKDIR}/.venv/bin:${PATH}"

# Command to run FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
