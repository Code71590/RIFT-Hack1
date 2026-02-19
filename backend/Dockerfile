# ═══════════════════════════════════════════════════════════════════
#  Backend Dockerfile — Flask API + Agent Pipeline
# ═══════════════════════════════════════════════════════════════════
FROM python:3.12-slim

# Install system dependencies (git for cloning repos, plus build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Configure git for the agent
RUN git config --global user.email "ai-agent@rift-hack.dev" && \
    git config --global user.name "AI-AGENT"

WORKDIR /app

# Copy requirements first (Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install flake8 and pytest (used by the agent pipeline)
RUN pip install --no-cache-dir flake8

# Copy the backend source code
COPY . .

# Create workspace directory for cloned repos
RUN mkdir -p /app/workspace /app/logs

# Expose port 5000
EXPOSE 5000

# Use gunicorn for production (threaded for SSE support)
RUN pip install --no-cache-dir gunicorn

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", "--timeout", "600", "app:app"]
