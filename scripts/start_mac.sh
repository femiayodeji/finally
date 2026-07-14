#!/usr/bin/env bash
# FinAlly — start script (macOS/Linux).
# Builds the Docker image if it doesn't exist (or if --build is passed),
# then runs the container with the db volume, port mapping, and .env file.
# Idempotent: safe to run multiple times.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IMAGE_NAME="finally"
CONTAINER_NAME="finally-app"
VOLUME_NAME="finally-data"
PORT="${FINALLY_PORT:-8000}"
ENV_FILE="$PROJECT_ROOT/.env"

cd "$PROJECT_ROOT"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Warning: $ENV_FILE not found. Copy .env.example to .env and set OPENROUTER_API_KEY." >&2
fi

# Already running? Nothing to do.
if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "FinAlly is already running at http://localhost:$PORT"
  exit 0
fi

BUILD=false
if [[ "${1:-}" == "--build" ]]; then
  BUILD=true
fi
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  BUILD=true
fi

if [[ "$BUILD" == true ]]; then
  echo "Building $IMAGE_NAME image..."
  docker build -t "$IMAGE_NAME" .
fi

# Remove a stopped leftover container from a previous run, if any.
if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  docker rm "$CONTAINER_NAME" >/dev/null
fi

docker volume create "$VOLUME_NAME" >/dev/null

ENV_FILE_ARGS=()
if [[ -f "$ENV_FILE" ]]; then
  ENV_FILE_ARGS=(--env-file "$ENV_FILE")
fi

docker run -d \
  --name "$CONTAINER_NAME" \
  -p "$PORT:8000" \
  -v "$VOLUME_NAME:/app/db" \
  "${ENV_FILE_ARGS[@]}" \
  "$IMAGE_NAME" >/dev/null

echo "FinAlly is starting at http://localhost:$PORT"

if command -v open >/dev/null 2>&1; then
  open "http://localhost:$PORT" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:$PORT" >/dev/null 2>&1 || true
fi
