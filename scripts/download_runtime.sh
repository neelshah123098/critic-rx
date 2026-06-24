#!/usr/bin/env bash
set -euo pipefail

MODEL_REPO_URL="${MODEL_REPO_URL:-https://huggingface.co/neelshah123098/criticleanGPT-Qwen3-8B-RL}"
MODEL_DIR="${MODEL_DIR:-runtime/criticleanGPT-Qwen3-8B-RL}"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required. Install git before downloading the runtime." >&2
  exit 1
fi

if ! git lfs version >/dev/null 2>&1; then
  echo "git-lfs is required because the runtime stores model.gguf and llama-server with Git LFS." >&2
  echo "Ubuntu/Debian: sudo apt install -y git-lfs && git lfs install" >&2
  exit 1
fi

git lfs install

if [ -d "$MODEL_DIR/.git" ]; then
  echo "Updating existing runtime clone: $MODEL_DIR"
  git -C "$MODEL_DIR" pull --ff-only
  git -C "$MODEL_DIR" lfs pull
elif [ -e "$MODEL_DIR" ]; then
  echo "Refusing to overwrite existing non-git path: $MODEL_DIR" >&2
  echo "Move it aside or set MODEL_DIR to a clean location." >&2
  exit 1
else
  mkdir -p "$(dirname "$MODEL_DIR")"
  git clone "$MODEL_REPO_URL" "$MODEL_DIR"
  git -C "$MODEL_DIR" lfs pull
fi

if [ -f "$MODEL_DIR/run.sh" ]; then
  chmod +x "$MODEL_DIR/run.sh"
fi
if [ -f "$MODEL_DIR/bin/llama-server" ]; then
  chmod +x "$MODEL_DIR/bin/llama-server"
fi

echo
echo "Runtime files:"
ls -lh "$MODEL_DIR/model.gguf" "$MODEL_DIR/bin/llama-server" "$MODEL_DIR/run.sh" 2>/dev/null || true

if [ ! -f "$MODEL_DIR/model.gguf" ] || [ ! -f "$MODEL_DIR/bin/llama-server" ]; then
  echo "Expected model.gguf and bin/llama-server were not found. Check the runtime clone." >&2
  exit 1
fi

model_size=$(wc -c < "$MODEL_DIR/model.gguf")
server_size=$(wc -c < "$MODEL_DIR/bin/llama-server")
if [ "$model_size" -lt 1000000000 ] || [ "$server_size" -lt 100000000 ]; then
  echo "The runtime files look too small. Git LFS may not have pulled the real artifacts." >&2
  echo "Try: git -C '$MODEL_DIR' lfs pull" >&2
  exit 1
fi

echo
echo "Runtime is ready at: $MODEL_DIR"
