# AML Memory Adapter — container image for the Code submission route.
# Platform: clone public repo -> docker build -> deploy -> run Add/Search smoke.
FROM python:3.11-slim

WORKDIR /app

# Install deps first so the layer is cached across source changes.
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source (runtime artifacts are excluded via .dockerignore).
COPY src/ .

EXPOSE 8000

# Listen on 0.0.0.0; honor a PORT env var if the platform injects one.
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
