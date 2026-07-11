# deploy/Dockerfile.backend
# ==============================================================================
# LOGISECURE AI - BACKEND IMAGE (FastAPI + Uvicorn)
#
# Build (from the repository root):
#   docker build -f deploy/Dockerfile.backend -t logisecure-backend .
#
# The interpreter is pinned (python:3.12-slim) so on-premise deployments are
# reproducible regardless of what teammates run locally.
#
# NOTE (production target): the AMD ROCm inference runtime is NOT baked into
# this image. Local GGUF inference will ship as a separate ROCm-based service
# (see README "Containerized Environment" for the /dev/kfd device passthrough).
# ==============================================================================

# ---------- Stage 1: build the dependency virtualenv ----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install
COPY requirements.txt /tmp/requirements.txt
COPY requirements-ai.txt /tmp/requirements-ai.txt
RUN pip install -r /tmp/requirements.txt

# Copy requirements-ai and install
COPY backend/requirements-ai.txt /tmp/requirements-ai.txt
RUN pip install -r /tmp/requirements-ai.txt

# ---------- Stage 2: minimal runtime image ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000

# Run as an unprivileged user: a compromised container must not own root.
RUN groupadd --system logisecure && useradd --system --gid logisecure --no-create-home logisecure

COPY --from=builder /opt/venv /opt/venv
COPY --chown=logisecure:logisecure . /app/

WORKDIR /app
USER logisecure

EXPOSE 8000

# Liveness probe against the /health endpoint (no curl in slim images, use stdlib).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\'PORT\',\'8000\')}/health', timeout=3)" || exit 1

# Environment variables for Fireworks AI
#ENV FIREWORKS_API_KEY=fw_BKbdwA3hHumdmnXzjSSoTh
#ENV FIREWORKS_MODEL="accounts/fireworks/models/llama-v3p1-8b-instruct"
#ENV FIREWORKS_BASE_URL="https://api.fireworks.ai/inference/v1"
ENV LLM_TEMPERATURE="0.3"
ENV LLM_MAX_TOKENS="500"
ENV DEBUG="False"
ENV CONFIDENCE_THRESHOLD="0.7"
ENV USE_MOCK_DATA="True"

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
