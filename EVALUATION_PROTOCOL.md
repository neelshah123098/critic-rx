# Evaluation Protocol

This document describes the submitted ClearRx inference and evaluation protocol
for AI4Math-2026 Track 1: Semantic Alignment Evaluation for Autoformalization
(FormalRx).

## Inference Pipeline

Each FormalRx row is processed independently. A row contains:

- `idx`
- `header`
- `informal_statement`
- `formal_statement`

For every row, ClearRx performs the following steps:

1. `IntentLens` extracts row-local informal-statement cues: quantifiers,
   variables, domains, constraints, functions, operators, constants, concepts,
   and conclusion surface.
2. `LeanLens` extracts row-local Lean-side cues: declaration kind/name,
   binders, hypotheses, variables, domains, constraints, operators, constants,
   target surface, and candidate spans.
3. `DeltaMap` creates neutral semantic checkpoints such as missing constraints,
   operator changes, domain mismatch, range mismatch, or Lean-specific
   truncation risk.
4. `TaxonomyLens` keeps the full FormalRx SCI-28 taxonomy available for every
   row and ranks likely categories using only current-row evidence.
5. `Evidence Composer` appends this non-authoritative row-local evidence to the
   pinned system prompt.
6. The Dockerized `criticleanGPT-Qwen3-8B-RL` runtime produces the final
   structured FormalRx diagnosis through a local OpenAI-compatible llama.cpp
   endpoint.
7. The runner parses, normalizes, validates, and writes JSONL predictions.

The output schema is:

```json
{
  "idx": "row id",
  "verdict": "aligned | misaligned",
  "error_category": "SCI-28 category or null",
  "error_segment": "minimal Lean fragment or null",
  "corrected_statement": "corrected Lean statement or null"
}
```

For aligned rows, `error_category`, `error_segment`, and
`corrected_statement` are written as JSON null.

## Endpoint Contract

The submitted runtime contract is:

- model: `criticleanGPT-Qwen3-8B-RL`
- API: non-streaming `/v1/chat/completions`
- `temperature=0`
- `max_tokens=1024`
- `stream=false`
- final user message follows `prompts/formalrx_prompt_template.txt`
- base system prompt follows `prompts/formalrx_system_prompt.md`

The row is not JSON-wrapped in the user message. Changing prompt shape,
streaming behavior, temperature, or token budget may change runtime behavior.

## Evaluation And Validation

The runner writes:

- predictions JSONL
- compact report JSON
- optional Codabench submission zip
- optional row-local prompt-context audit JSONL

Before upload, predictions can be validated with:

```bash
python scripts/validate_predictions.py \
  --dataset data/FormalRx_Test.jsonl \
  --predictions outputs/formalrx_full_predictions.jsonl \
  --expected-count 7030
```

The Codabench archive contains exactly one file named `predictions.jsonl`.

## Same-Problem-Level Information Disclosure

No information from other levels, variants, reformulations, or related rows of
the same problem is used during inference.

Each prediction is computed from exactly one FormalRx row:

```text
(header, informal_statement, formal_statement) -> one diagnosis
```

The submitted inference path does not use:

- other levels of the same problem;
- other rows from the test set as context;
- retrieval over test rows or derivatives of test rows;
- cross-row memory;
- manual test-sample annotation;
- leaderboard-result probing.

## External Tools, APIs, Search Engines, And Auxiliary Systems

During inference, the only model endpoint used is the local
Dockerized OpenAI-compatible llama.cpp server for
`criticleanGPT-Qwen3-8B-RL`.

Auxiliary systems used by the reproducibility package:

- Hugging Face Hub download utilities to retrieve the FormalRx test set during
  setup;
- Git LFS to clone the `neelshah123098/criticleanGPT-Qwen3-8B-RL` runtime
  repository and pull `model.gguf` plus `bin/llama-server`;
- Docker with NVIDIA GPU support to build and run the local runtime image;
- Python standard-library JSON, HTTP, validation, and zip-writing utilities;
- deterministic ClearRx premodel modules in this repository.

The submitted inference path does not use external search engines, web search,
remote LLM APIs, retrieval databases, or another generative model.

## Dependencies And Environment

Python dependency:

```text
huggingface_hub>=0.23.0
```

Python version:

```text
>=3.10
```

Runtime environment:

- Linux x86-64 NVIDIA host with a working driver visible through `nvidia-smi`;
- Docker with NVIDIA GPU support;
- Git and Git LFS for cloning the runtime repository;
- default runtime launch maps host port `8001` to container port `8000` and
  uses `N_GPU_LAYERS=99` and `CTX_SIZE=16384`.

## Reproduction Commands

```bash
git clone https://github.com/neelshah123098/critic-rx.git
cd critic-rx

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python scripts/download_dataset.py \
  --repo-id LARK-Lab/FormalRx-Test \
  --output data/FormalRx_Test.jsonl

bash scripts/download_runtime.sh

bash scripts/start_runtime.sh

bash scripts/run_smoke_10.sh
bash scripts/run_smoke_100.sh

python -m clearrx.run_formalrx \
  --dataset data/FormalRx_Test.jsonl \
  --base-url http://127.0.0.1:8001/v1 \
  --model criticleanGPT-Qwen3-8B-RL \
  --timeout 300 \
  --max-tokens 1024 \
  --output outputs/formalrx_full_predictions.jsonl \
  --report outputs/formalrx_full_report.json \
  --zip-output outputs/formalrx_full_predictions.zip
```
