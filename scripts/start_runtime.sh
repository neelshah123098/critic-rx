#!/usr/bin/env bash
set -euo pipefail

MODEL_DIR="${MODEL_DIR:-runtime/criticleanGPT-Qwen3-8B-RL}"
IMAGE_NAME="${IMAGE_NAME:-criticleangpt-qwen3-8b-rl-formalrx:local}"
HOST_PORT="${HOST_PORT:-8001}"
CONTAINER_PORT="${CONTAINER_PORT:-8000}"
CTX_SIZE="${CTX_SIZE:-16384}"
N_GPU_LAYERS="${N_GPU_LAYERS:-99}"

if [ ! -d "$MODEL_DIR" ]; then
  echo "Missing runtime directory: $MODEL_DIR" >&2
  echo "Run: bash scripts/download_runtime.sh" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for the submitted runtime path." >&2
  exit 1
fi

if [ "${USE_COMPOSE:-0}" = "1" ]; then
  if [ ! -f "$MODEL_DIR/docker-compose.yml" ]; then
    echo "Missing $MODEL_DIR/docker-compose.yml" >&2
    exit 1
  fi
  cd "$MODEL_DIR"
  exec docker compose up --build
fi

if [ ! -f "$MODEL_DIR/Dockerfile" ]; then
  echo "Missing $MODEL_DIR/Dockerfile" >&2
  echo "The current runtime is expected to be the Docker-first FormalRx package." >&2
  exit 1
fi

docker build -t "$IMAGE_NAME" "$MODEL_DIR"

exec docker run --rm --gpus all \
  -p "$HOST_PORT:$CONTAINER_PORT" \
  -e CTX_SIZE="$CTX_SIZE" \
  -e N_GPU_LAYERS="$N_GPU_LAYERS" \
  "$IMAGE_NAME"
