# Previous UMGL-Forensics -> Role 5 mapping

This document records which parts of the previous
`UMGL-Forensics` architecture were reused by Role 5 and which were
intentionally dropped. The previous project was a 16-microservice
Rust + Python + TypeScript platform; Role 5 is a single Python
package that emits the same risk JSON contract and event shapes.

| Previous component                                | Reused? | Role 5 replacement                                       |
| ------------------------------------------------- | ------- | -------------------------------------------------------- |
| `async-axum` HTTP gateway                         | no      | Celery tasks in `platform/app/tasks`                     |
| NATS JetStream fan-out                            | no      | `emit_event` helper (Redis list + pub/sub)               |
| Kafka subject/signal telemetry                    | no      | `signal_scores` table values produced in-memory          |
| PostgreSQL persistence                            | yes     | data prepared for `influencer_scores` / `signal_scores`  |
| Neo4j full graph analytics                        | no      | `graph_proxy_score` from local cluster evidence          |
| Qdrant vector store                               | no      | accepts `semantic_signal_score` if available             |
| MongoDB raw behavioral metadata                   | partial | consumed if present                                      |
| Redis direct writes                               | no      | events/state via helpers only                            |
| `semantic.py`                                     | yes     | `backend.pipeline.analysis` (lexicon + optional backend)  |
| `behavioral.py`                                    | yes     | `backend.pipeline.analysis.fake_engagement`               |
| `graph.py`                                        | partial | `backend.pipeline.fusion.components.graph_proxy_score` |
| `bot_rings.py`                                    | yes     | `backend.pipeline.analysis.coordinated_engagement`        |
| `final_risk.py`                                   | yes     | `backend.pipeline.fusion.fusion`            |
| `risk-score.schema.json`                          | yes     | emitted by `run_role5_pipeline`                          |
| `signal_scores` table writes                      | yes     | produced in-memory in `sub_scores` / `signal_scores`     |
| Campaign detection service                        | no      | local per-record category classification                 |
| Explainability service                            | yes     | `backend.pipeline.analysis.reason_builder`                |
| Tenant onboarding / JWT / API keys                | no      | unchanged                                                 |
| Admin dashboard                                   | no      | unchanged                                                 |
| Terraform / Helm / Prometheus                     | no      | unchanged                                                 |
| Notification service                              | no      | unchanged                                                 |

## Five-layer mapping

The previous project's 5-layer ensemble maps to:

| Previous layer   | Role 5 module                                                        |
| ---------------- | -------------------------------------------------------------------- |
| Semantic         | `semantic_signal_score` (lib/risk_components)                        |
| Behavioral       | `behavioral_signal_score` (lib/risk_components)                      |
| Graph            | `graph_proxy_score` (lib/risk_components)                            |
| Bot rings        | `bot_ring_signal_score` (lib/risk_components)                        |
| Final risk       | `renormalized_fusion.fuse` -> canonical risk JSON                    |

## Risk JSON mapping

`risk-score.schema.json` (previous):

```json
{
  "score": 0.84,
  "components": {},
  "model_version": "string",
  "computed_at": "ISO_TIMESTAMP"
}
```

Role 5 output (additive only):

```json
{
  "score": 0.84,
  "risk_category": "high",
  "components": {
    "semantic":     { "score": 0.82, "weight": 0.20, "contribution": 0.164, "available": true },
    "behavioral":   { "score": 0.61, "weight": 0.30, "contribution": 0.183, "available": true },
    "graph_proxy":  { "score": 0.94, "weight": 0.20, "contribution": 0.188, "available": true },
    "bot_rings":    { "score": 0.88, "weight": 0.20, "contribution": 0.176, "available": true },
    "brand_safety": { "score": 0.70, "weight": 0.10, "contribution": 0.070, "available": true }
  },
  "renormalized": false,
  "model_version": "Role5-FakeDetectionScore-v1",
  "computed_at": "ISO_TIMESTAMP"
}
```

`subject_id`, `subject_type`, `evidence`, and `features` from the
previous schema continue to be available on the parent
`Role5PipelineResult` (`influencer_id`, `mentions`, `analysis`).
