# Multi-stage build: compile the Vue frontend, then run it via FastAPI's
# static mount so the whole app is one container on :8000.

# --- Frontend build stage ---
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci
COPY frontend/ ./frontend/
RUN cd frontend && npm run build

# --- Runtime stage ---
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ ./backend/
COPY --from=build /app/frontend/dist ./frontend/dist
WORKDIR /app/backend
EXPOSE 8000
ENV ORACLE_DSN=host.docker.internal:1521/FREEPDB1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
