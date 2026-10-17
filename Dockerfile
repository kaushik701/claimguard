# ClaimGuard: API + built React app on one port (CPU only). Build: docker build -t claimguard .
# Run: docker run -p 8000:8000 -e GROQ_API_KEY=... -e CLAIMGUARD_PUBLIC_DEMO=1 claimguard
FROM node:20-slim AS web
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV HOME=/app FASTEMBED_CACHE_PATH=/app/.fastembed PYTHONUNBUFFERED=1
COPY backend/pyproject.toml backend/
RUN pip install --no-cache-dir -e backend/ || true
COPY . .
RUN pip install --no-cache-dir -e backend/
COPY --from=web /app/frontend/dist frontend/dist
# The built knowledge base is committed; build it only if missing (needs OCR, ~3 min)
RUN cd backend && ([ -f ../knowledge/build/clauses.json ] || python -m claimguard.kb build)
ENV CLAIMGUARD_PUBLIC_DEMO=1
# Hugging Face runs the container as user 1000: make app data writable
RUN mkdir -p data && chmod -R a+rwX /app
EXPOSE 8000
CMD ["sh", "-c", "cd backend && uvicorn claimguard.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
