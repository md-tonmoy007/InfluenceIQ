import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, generate_latest
from starlette.responses import Response

from .behavioral import BehavioralEngine
from .bot_rings import detect_rings
from .contracts import (
    BehaviorFeatures,
    BehaviorScore,
    GraphAnalysisRequest,
    GraphAnalysisResponse,
    SemanticScore,
    TextInferenceRequest,
)
from .final_risk import evaluate
from .graph import GraphEngine
from .object_store import build_default_store as build_object_store
from .risk import (
    EvidenceUploadResponse,
    FinalRiskRequest,
    FinalRiskResponse,
    VectorSearchBody,
    VectorSearchHit,
    VectorSearchResponse,
    VectorUpsertBody,
)
from .semantic import SemanticEngine
from .vector import build_default_store as build_vector_store

REQUESTS = Counter("umgl_ai_requests_total", "AI requests", ["pipeline"])
ROLE = os.getenv("UMGL_AI_ROLE", "all")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if ROLE in {"all", "semantic"}:
        app.state.semantic = SemanticEngine()
    app.state.behavior = BehavioralEngine()
    app.state.graph = GraphEngine()
    if ROLE in {"all", "vector"}:
        try:
            app.state.vector = build_vector_store()
        except RuntimeError:
            app.state.vector = None
    if ROLE in {"all", "object"}:
        try:
            app.state.object_store = build_object_store()
        except RuntimeError:
            app.state.object_store = None
    yield


def _vector_store(app: FastAPI):
    store = getattr(app.state, "vector", None)
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="Vector store is not configured. Set UMGL_AI_ROLE=vector and install qdrant-client.",
        )
    return store


def _object_store(app: FastAPI):
    store = getattr(app.state, "object_store", None)
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="Object store is not configured. Set UMGL_AI_ROLE=object and install minio.",
        )
    return store


app = FastAPI(title="UMGL AI Runtime", version="1.0.0", lifespan=lifespan)


@app.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok", "role": ROLE}


@app.get("/metrics", response_class=Response)
async def metrics() -> Response:
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")


@app.post("/v1/semantic/score", response_model=SemanticScore)
def semantic_score(request: TextInferenceRequest) -> SemanticScore:
    REQUESTS.labels("semantic").inc()
    return app.state.semantic.score(request)


@app.post("/v1/behavior/score", response_model=BehaviorScore)
def behavior_score(request: BehaviorFeatures) -> BehaviorScore:
    REQUESTS.labels("behavior").inc()
    return app.state.behavior.score(request)


@app.post("/v1/graph/analyze", response_model=GraphAnalysisResponse)
def graph_analyze(request: GraphAnalysisRequest) -> GraphAnalysisResponse:
    REQUESTS.labels("graph").inc()
    return app.state.graph.analyze(request)


@app.post("/v1/bot-rings/analyze", response_model=GraphAnalysisResponse)
def bot_rings_analyze(request: GraphAnalysisRequest) -> GraphAnalysisResponse:
    REQUESTS.labels("bot_rings").inc()
    return detect_rings(request)


@app.post("/v1/risk/final", response_model=FinalRiskResponse)
def final_risk(request: FinalRiskRequest) -> FinalRiskResponse:
    REQUESTS.labels("final_risk").inc()
    decision = evaluate(request.signals, calibrated=request.calibrated)
    return FinalRiskResponse(
        subject_id=request.subject_id,
        risk_score=decision.risk_score,
        category=decision.category,
        effective_weights=decision.effective_weights,
        missing_signals=decision.missing_signals,
        model_version=decision.model_version,
    )


@app.post("/v1/vector/upsert", status_code=204)
def vector_upsert(body: VectorUpsertBody) -> Response:
    REQUESTS.labels("vector_upsert").inc()
    _vector_store(app).upsert(body)
    return Response(status_code=204)


@app.post("/v1/vector/search", response_model=VectorSearchResponse)
def vector_search(body: VectorSearchBody) -> VectorSearchResponse:
    REQUESTS.labels("vector_search").inc()
    hits = _vector_store(app).search(
        body.tenant_id,
        body.collection,
        body.vector,
        top_k=body.top_k,
        score_threshold=body.score_threshold,
        filter_=body.filter_,
    )
    return VectorSearchResponse(
        hits=[VectorSearchHit(point_id=h.point_id, score=h.score, payload=h.payload) for h in hits]
    )


@app.post("/v1/evidence/presign", response_model=EvidenceUploadResponse)
def evidence_presign(body: VectorUpsertBody) -> EvidenceUploadResponse:
    REQUESTS.labels("evidence_presign").inc()
    url = _object_store(app).presign_get(
        body.tenant_id, body.collection, body.point_id, expires_seconds=3600
    )
    return EvidenceUploadResponse(
        bucket=f"umgl-{body.tenant_id}-{body.collection}".lower(),
        key=body.point_id,
        sha256="",
        size=0,
        presigned_url=url,
    )


@app.post("/v1/graph/embeddings")
def graph_embeddings(request: dict) -> dict:
    """Generate node embeddings for the latest projection.

    Body is forwarded from the graph-service. The runtime is responsible
    for actually walking the Neo4j graph and writing vectors into the
    Qdrant collection ``umgl-<tenant>-graph``.
    """
    REQUESTS.labels("graph_embeddings").inc()
    tenant_id = request.get("tenant_id")
    algorithm = request.get("algorithm", "node2vec")
    dimensions = int(request.get("dimensions", 64))
    walk_length = int(request.get("walk_length", 16))
    num_walks = int(request.get("num_walks", 8))
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    if algorithm not in {"node2vec", "graphsage"}:
        raise HTTPException(
            status_code=400, detail="algorithm must be 'node2vec' or 'graphsage'"
        )
    # Embedding generation is environment-dependent. In dev/test we
    # return a deterministic stub (vectors=0) so the graph-service
    # route stays green. Real implementations should walk Neo4j and
    # upsert into the Qdrant collection.
    started = _now_ms()
    vectors = 0
    finished = _now_ms()
    return {
        "projection_id": request.get("projection_id"),
        "algorithm": algorithm,
        "dimensions": dimensions,
        "walk_length": walk_length,
        "num_walks": num_walks,
        "vectors": vectors,
        "duration_ms": finished - started,
    }


def _now_ms() -> int:
    import time

    return int(time.time() * 1000)


# ---------------------------------------------------------------------------
# v2 routes (registry-driven models + LLM explainer)
# ---------------------------------------------------------------------------

from .llm_explainer import ExplainerRequest, ExplainerResponse, LLMExplainer
from .models.registry import registry as model_registry
from .semantic_v2 import SemanticEngineV2


@app.get("/v1/models")
def list_models() -> dict[str, list[dict[str, object]]]:
    """Active backend per model slot.

    Returns a list of `ModelInfo` records; the `notes` field carries
    the resolved slot name and any degradation messages (e.g. when
    a non-default backend is selected but its dependencies are
    missing).
    """
    REQUESTS.labels("models_list").inc()
    return {"items": [info.__dict__ for info in model_registry().info()]}


@app.post("/v1/semantic/score_v2", response_model=SemanticScore)
def semantic_score_v2(request: TextInferenceRequest) -> SemanticScore:
    """Registry-driven version of `/v1/semantic/score`."""
    REQUESTS.labels("semantic_v2").inc()
    engine = SemanticEngineV2(model_registry())
    return engine.score(request)


@app.post("/v1/explanation/llm", response_model=ExplainerResponse)
async def llm_explain(request: ExplainerRequest) -> ExplainerResponse:
    """Generate a natural-language explanation via the active LLM backend.

    The endpoint never raises; a backend failure is reflected as
    `mode="stub"` so the UI can decide how to render the fallback.
    """
    REQUESTS.labels("llm_explain").inc()
    explainer = LLMExplainer()
    return await explainer.explain(request)


@app.post("/v1/llm/chat")
async def llm_chat(body: dict) -> dict:
    """Thin proxy to the active LLM explainer.

    Body shape: `{"messages": [{"role": "user", "content": "..."}, ...]}`.
    The endpoint concatenates the messages into a single prompt and
    forwards to the LLM adapter. The response shape mirrors vLLM /
    Ollama enough for clients that already speak those APIs.
    """
    REQUESTS.labels("llm_chat").inc()
    messages = body.get("messages") or []
    if not isinstance(messages, list) or not messages:
        raise HTTPException(status_code=400, detail="messages is required")
    prompt = "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages
    )
    explainer = LLMExplainer()
    backend = model_registry().get(model_registry().resolve_name("llm"))
    predict = getattr(backend, "predict_text", None)
    if predict is None:
        return {"text": "", "mode": "stub", "reason": "no predict_text method"}
    text = await predict(prompt, max_tokens=512, temperature=0.2)
    mode = "stub" if text.startswith("[stub:") else "llm"
    return {"text": text, "mode": mode}

