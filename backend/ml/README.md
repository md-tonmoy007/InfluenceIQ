# backend.ml — optional ML backends for InfluenceIQ

`backend.ml` is the **optional** model-serving package that powers the v2 adapters in
`backend.pipeline.fusion.backends.ml_adapters`. The core InfluenceIQ backend
**does not** require this package — every heuristic in `backend.pipeline/` falls
back to a deterministic implementation when the adapter is disabled or when
`backend.ml` is not importable.

## What it provides

* A FastAPI app (`api.py`) exposing the registered model slots under
  `/v1/semantic/score`, `/v1/behavior/score`, `/v1/graph/analyze`,
  `/v1/bot-rings/analyze`, `/v1/risk/final`, `/v1/semantic/score_v2`,
  `/v1/explanation/llm`, and a registry dump at `/v1/models`.
* A pluggable model registry (`models/registry.py`) that maps slot names
  (`spam`, `toxicity`, `aigc`, `llm`, `gnn`, …) to backend implementations.
* Reference adapters for BERT-MoE, DistilBERT spam, DeBERTa spam, RoBERTa AIGC,
  ToxicBERT, Llama explainer, GAT, GCN, GraphSAGE, GGT.
* Pluggable vector store (Qdrant), document store (MongoDB), and object store (MinIO) backends.

## Install

`backend/ml` is kept in-tree. The default backend uv environment does not install the
heavy ML-only dependencies automatically; add them separately when you enable these
adapters.

## Run the FastAPI service

```bash
# starts on port 8080 by default
python -m backend.ml.api

# or via uvicorn
uvicorn backend.ml.api:app --host 0.0.0.0 --port 8080
```

## Wire it into the scoring pipeline

The adapters in `backend/pipeline/fusion/backends/ml_adapters.py` are
controlled by environment flags — see that file's docstring. In short:

| Env var | Effect |
| ------- | ------ |
| `ML_USE_SEMANTIC_V2=1`     | Use the registry-driven semantic engine |
| `ML_USE_BEHAVIORAL_V2=1`   | Use the calibrated behavioral engine |
| `ML_USE_GRAPH_V2=1`        | (Inert in v1) |
| `ML_USE_BOT_RINGS_V2=1`    | (Inert in v1) |
| `ML_USE_LLM_EXPLAINER=1`   | Call the LLM explainer for natural-language reasons |

All flags default to off. When the flag is off, the adapter is a no-op and the
heuristic path runs unchanged.

## Why it is optional

* The torch / transformers / peft stack is multi-GB. Keeping it out of the
  default image keeps the dev Docker build fast and the attack surface small.
* Every adapter gracefully degrades. The scoring pipeline's deterministic
  behaviour is byte-for-byte identical with or without `backend.ml` installed.
* This makes CI cheap (no model downloads) and lets ops teams roll out the ML
  stack per-tenant if/when they want to.

## Tests

```bash
cd backend/ml
pytest tests/ -q
```

The unit tests use stub backends and a fake `backend.ml` module injected via
`sys.modules` — they do **not** download any model weights.
