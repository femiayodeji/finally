#!/usr/bin/env bash
# FinAlly — stop script (macOS/Linux).
# Stops and removes the running container. Does NOT remove the data volume,
# so the portfolio/watchlist persist across restarts. Idempotent.
set -euo pipefail

CONTAINER_NAME="finally-app"

if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "Stopping $CONTAINER_NAME..."
  docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
  docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
  echo "Stopped. Data volume 'finally-data' preserved."
else
  echo "$CONTAINER_NAME is not running."
fi
