# Role 5 Implementation

Role 5 is implemented in `scoring_service` and keeps the published Celery contracts in `platform/app/tasks` unchanged.

## Boundaries

- Extraction parses raw page text, optional HTML, supplied social links, credentials, titles, authority mentions, and context.
- spaCy PERSON NER is optional. Missing spaCy or `en_core_web_sm` falls back to deterministic extraction.
- Identity resolution uses normalized URL hashes, RapidFuzz-compatible name/username matching, and an ambiguous-pair handoff. It never calls an external LLM.
- Full graph analytics remain outside Role 5. Local cluster evidence only produces `graph_proxy_score` and `bot_ring_signal_score`.
- Adapters emit events only through `emit_event`; service modules do not write to Redis.

## Public Entry Points

- `extract_influencer_mentions(page)` returns auditable mention records.
- `resolve_identity_clusters(candidates)` returns `canonical`, `ambiguous_pairs`, and `merge_events`.
- `build_role5_scores(candidate, campaign)` returns all signal scores, analyses, evidence, reasons, caps, and canonical risk JSON.
- `build_influencer_output(candidate, campaign)` returns the frontend/backend influencer contract.
- `build_sub_scores(candidate, campaign)` retains the legacy five-score view for existing consumers.

## Model Replacement

Every analyzer accepts feature dictionaries and has no hard provider dependency. Model probabilities can be supplied by upstream services. Fake-comment scoring blends `model_fake_probability` only when present; otherwise it uses the documented deterministic formula.

Optional API-backed model classifiers are also available for production experiments:

| Env var | Default | Effect |
| ------- | ------- | ------ |
| `ROLE5_USE_MODEL_CLASSIFIERS` | unset | Set to `1` to enable external model calls. |
| `OPENAI_API_KEY` | unset | Required when API-backed classifiers are enabled. |
| `ROLE5_MODEL_CLASSIFIER_MODEL` | `OPENAI_JUDGE_MODEL` or `gpt-4o-mini` | Model used for Role-5 classification. |
| `ROLE5_MODEL_CLASSIFIER_TIMEOUT` | `8` | Request timeout in seconds. |

The optional classifiers cover fake comments, suspicious followers, bot behavior, brand safety, and sentiment quality. All calls fail closed: if the model is disabled, the key is missing, the network fails, or the response cannot be parsed, Role 5 returns the deterministic heuristic score.

## Testing

Run:

```powershell
$env:PYTHONPATH='platform;.'
python -m pytest scoring_service\tests tests\test_role5.py -q
```

The suite covers five HTML fixtures, optional NER fallback, extraction, identity passes, all fake-risk formulas, brand safety, credibility, sentiment suppression, renormalization, trust caps, explanations, and output contracts.
