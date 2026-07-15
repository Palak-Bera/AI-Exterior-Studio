#!/bin/sh
set -e

# Railway (and most PaaS) inject PORT; default 8000 for local Docker.
PORT="${PORT:-8000}"

echo "[entrypoint] Preparing AI Exterior Studio backend..."

python scripts/generate_textures.py || true

# Optional one-shot download onto a mounted volume (e.g. Railway Volume at /app/storage).
# Keep off by default — first download can take many minutes / several GB.
if [ "${AUTO_DOWNLOAD_MODELS:-false}" = "true" ]; then
  echo "[entrypoint] AUTO_DOWNLOAD_MODELS=true — syncing weights into storage/models..."
  python scripts/download_models.py || echo "[entrypoint] Model download failed (server will still start)."
fi

echo "[entrypoint] Starting uvicorn on 0.0.0.0:${PORT} (LOG_LEVEL=${LOG_LEVEL:-INFO})"
echo "[entrypoint] Grounded SAM warms in the background after start (CPU can take a few minutes)."
echo "[entrypoint] Model weights: set AUTO_DOWNLOAD_MODELS=true or run 'python scripts/download_models.py' if storage/models is empty."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
