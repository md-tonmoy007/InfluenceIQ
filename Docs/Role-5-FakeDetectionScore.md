# Role 5 - Extraction, Fake Detection & Scoring

Role 5 of InfluenceIQ turns raw scraped pages into **explainable,
auditable trust and fake-risk scores** for every candidate influencer.
It is implemented inside `backend.pipeline/` and reuses only the parts
of the previous UMGL-Forensics architecture that the spec calls for:

* the 5-layer fake-detection ensemble
* the canonical `risk_score` JSON contract
* the `signal_scores` table concept
* renormalized weighted fusion
* detection-before-final-scoring
* source-based evidence and explainability
* event payloads for `influencer.found`, `identity.merged`, `score.calculated`

It deliberately does **not** rebuild the full UMGL Rust+Python+TS
microservice platform, NATS, Kafka, Neo4j projection workers, or the
MinIO/Qdrant storage layers.

---

## 1. Package layout

```
backend.pipeline/
├── __init__.py
├── models.py                  TypedDict contracts
├── worker.py                  Celery factory
├── detection/                 Pipeline 3 + per-detector wrappers
│   ├── __init__.py
│   ├── detection_classifier.py    SAFE/SUSPICIOUS/HIGH_RISK/... rules
│   ├── fake_comment_detector.py   Pipeline 4 wrapper
│   ├── fake_follower_detector.py  Pipeline 5 wrapper
│   ├── bot_behavior_detector.py   Pipeline 6 wrapper
│   ├── coordinated_ring_detector.py Pipeline 7 wrapper
│   └── brand_safety_detector.py   Pipeline 13 wrapper
├── analysis/                  Sub-score calculations
│   ├── engagement_quality.py  Pipeline 11
│   ├── source_confidence.py   Pipeline 15
│   ├── sentiment_backends.py  Pipeline 12 multi-backend
│   ├── reason_builder.py      Pipeline 18 explainability
│   ├── credibility.py         Pipeline 14
│   ├── brand_safety_blocklist.py
│   ├── fake_comment.py
│   ├── fake_follower.py
│   ├── bot_behavior.py
│   ├── coordinated_engagement.py
│   ├── sentiment.py
│   └── fake_engagement.py
├── scoring/                   Final trust + risk JSON
│   ├── renormalized_fusion.py Pipeline 10
│   ├── trust_formula.py       Pipeline 16
│   ├── role5_fusion.py        Legacy fusion used by adapters
│   ├── risk_components.py     Per-layer signal score helpers
│   ├── sub_scores.py          Orchestrator (legacy path)
│   ├── normalize.py
│   └── versioning.py          Role5-FakeDetectionScore-v1
├── identity/                  Pipeline 2 - 3-pass identity resolution
│   ├── resolver.py
│   ├── canonical.py
│   ├── fuzzy_match.py
│   └── url_match.py
├── extraction/                Pipeline 1 + PII extraction
│   ├── parser.py              HTML parsing
│   ├── entities.py            PERSON NER + deterministic fallback
│   ├── handles.py             @handle, URL normalization
│   ├── social_urls.py         Profile URL extraction
│   ├── credentials.py         Credentials, titles, authority
│   └── contact_info.py        Email / phone / website / address extraction
├── events/                    Pipeline 19
│   └── __init__.py            InfluencerFound/IdentityMerged/ScoreCalculated
├── pipeline/                  Pipeline 1-20 orchestrator
│   └── orchestrator.py        run_role5_pipeline(candidate, campaign)
├── tests/                     5 HTML fixtures + 100+ unit tests
└── docs/                      (this file lives in /Docs)
```

---

## 2. Pipeline summary

| #   | Pipeline                          | Module                                     |
| --- | --------------------------------- | ------------------------------------------ |
| 1   | Information extraction            | `backend.pipeline.extraction.*`             |
| 2   | Identity resolution (3-pass)      | `backend.pipeline.identity.*`               |
| 3   | Detection category                | `backend.pipeline.detection.detection_classifier` |
| 4   | Fake comment detection            | `backend.pipeline.detection.fake_comment_detector` |
| 5   | Fake follower detection           | `backend.pipeline.detection.fake_follower_detector` |
| 6   | Bot behavior detection            | `backend.pipeline.detection.bot_behavior_detector` |
| 7   | Coordinated engagement detection  | `backend.pipeline.detection.coordinated_ring_detector` |
| 8   | Overall fake risk                 | `backend.pipeline.fusion.components.overall_fake_risk` |
| 9   | Previous 5-layer mapping          | `backend.pipeline.fusion.components.*_signal_score` |
| 10  | Renormalized weighted fusion      | `backend.pipeline.fusion.fusion` |
| 11  | Engagement quality                | `backend.pipeline.analysis.engagement_quality` |
| 12  | Sentiment (multi-backend)         | `backend.pipeline.analysis.sentiment_backends` |
| 13  | Brand safety detection            | `backend.pipeline.detection.brand_safety_detector` |
| 14  | Credibility                       | `backend.pipeline.analysis.credibility`     |
| 15  | Source confidence                 | `backend.pipeline.analysis.source_confidence` |
| 16  | Role 5 final trust score          | `backend.pipeline.fusion.trust`    |
| 17  | Final output JSON                 | `backend.pipeline.orchestrator.run_role5_pipeline` |
| 18  | Explainability                    | `backend.pipeline.analysis.reason_builder`  |
| 19  | Events                            | `backend.pipeline.events.*`                 |
| 20  | Testing                           | `backend.pipeline.tests`                    |
| --  | Contact info extraction (PII)     | `backend.pipeline.extraction.contact_info`  |

---

## 3. Detection categories (Pipeline 3)

The classifier applies the spec's risk-band rules in order:

| Condition                                                    | Category              |
| ------------------------------------------------------------ | --------------------- |
| `coordinated_engagement_risk_score > 80`                     | `SPAM_RING`           |
| `bot_behavior_risk_score > 70`                               | `BOT_LIKE`            |
| `fake_follower_risk_score > 70`                              | `FAKE_FOLLOWER`       |
| `fake_comment_risk_score > 70`                               | `FAKE_COMMENT`        |
| `brand_safety_score < 40`                                    | `BRAND_RISK`          |
| `41 <= overall_fake_risk_score <= 65`                        | `HIGH_RISK`           |
| `21 <= overall_fake_risk_score <= 40`                        | `SUSPICIOUS`          |
| `overall_fake_risk_score <= 20`                              | `SAFE`                |
| `data_source_count < 3 and overall_fake_risk_score > 40`     | `NEEDS_HUMAN_REVIEW`  |

Per-detector booleans (`is_fake_comment`, `is_fake_follower`,
`is_bot_like`, `is_spam_ring`) are always set, so the dashboard can
display *which* rules fired even when the final category is something
else.

---

## 4. Five-layer ensemble (Pipeline 9)

| Layer        | Inputs                                                                                                | Default weight |
| ------------ | ----------------------------------------------------------------------------------------------------- | -------------- |
| semantic     | `spam_probability`, `toxicity_probability`, `aigc_probability`, `claim_mismatch_score`, propaganda, talking-point | 0.20           |
| behavioral   | `fake_follower_risk_score`, `fake_comment_risk_score`, `bot_behavior_risk_score`, posting uniformity, velocity, duplicates, night activity | 0.30 |
| graph_proxy  | `repeated_commenter_cluster_score`, `duplicate_text_cluster_score`, `suspicious_account_overlap_score`, `shared_hashtag_cluster_score`, `same_source_cluster_score` | 0.20 |
| bot_rings    | `coordinated_engagement_risk_score`, `confirmed_bot_overlap_score`, `amplifier_account_ratio`, `synchronized_activity_score` | 0.20 |
| brand_safety | `100 - brand_safety_score`                                                                            | 0.10           |

When a layer has no evidence, its weight is dropped and the remaining
weights are rescaled to sum to one. The `renormalized` flag and the
`available_layers` / `missing_layers` lists are surfaced in the output
JSON.

---

## 5. Trust score (Pipeline 16)

```
positive_trust = 0.20*relevance + 0.20*credibility
               + 0.15*engagement_quality + 0.15*sentiment
               + 0.15*brand_safety + 0.15*source_confidence

fake_risk_penalty = 0.50 * overall_fake_risk_score

role5_trust = clamp(positive_trust - fake_risk_penalty, 0, 100)
```

Hard caps (applied in order):

* `overall_fake_risk_score > 80` -> trust at most 45.
* Severe brand-safety flag -> trust at most 40.
* `data_source_count < 3` -> trust at most 70.

Grades: `A+ 90..100`, `A 80..89`, `B 70..79`, `C 60..69`, `D 40..59`,
`F 0..39`.

---

## 6. Risk JSON contract

```json
{
  "score": 0.32,
  "risk_category": "suspicious",
  "components": {
    "semantic":    { "score": 0.25, "weight": 0.20, "contribution": 0.05,    "available": true  },
    "behavioral":  { "score": 0.41, "weight": 0.30, "contribution": 0.123,   "available": true  },
    "graph_proxy": { "score": 0.22, "weight": 0.20, "contribution": 0.044,   "available": true  },
    "bot_rings":   { "score": 0.22, "weight": 0.20, "contribution": 0.044,   "available": true  },
    "brand_safety":{ "score": 0.05, "weight": 0.10, "contribution": 0.005,   "available": true  }
  },
  "renormalized": false,
  "model_version": "Role5-FakeDetectionScore-v1",
  "computed_at": "ISO_TIMESTAMP"
}
```

The model identifier is exposed as
`backend.pipeline.fusion.versioning.MODEL_VERSION`. The previous alias
`Role5-FakeSignal-v1` is kept for backward compatibility.

---

## 7. Event payloads (Pipeline 19)

* `influencer.found`     -> `{name, platform, source}`
* `identity.merged`      -> `{canonical_id, merged_from, confidence}`
* `score.calculated`     -> full struct from
  `backend.pipeline.events.ScoreCalculated.to_payload()`

The Celery adapters call `emit_event` from
`backend.core.cache.pipeline_state`; the score adapter builds the payload via
the `ScoreCalculated` helper so the field set is always identical.

---

## 8. Celery task contracts (unchanged)

| Task name                                  | Signature                                                      |
| ------------------------------------------ | -------------------------------------------------------------- |
| `backend.pipeline.tasks.extract.extract_influencers`    | `extract_influencers(campaign_id: str, page: dict) -> list[dict]` |
| `backend.pipeline.tasks.extract.resolve_identity_llm`   | `resolve_identity_llm(candidate_a: dict, candidate_b: dict) -> dict` |
| `backend.pipeline.tasks.score.classify_brand_safety`    | `classify_brand_safety(campaign_id: str, content: dict) -> dict` |
| `backend.pipeline.tasks.score.score_influencer`         | `score_influencer(campaign_id: str, influencer_id: str, sub_scores: dict) -> dict` |

These signatures are pinned by `Contracts-Day1.md` and are not changed
by this work. The adapters delegate to the `backend.pipeline` package
internally.

---

## 9. Model replaceability

Every analyzer in this package accepts a feature dictionary and has
no provider dependency. To swap the model behind a fake-comment
detector, override the call to `backend.pipeline.analysis.fake_comment.score_fake_comments`
in the pipeline orchestrator or supply `model_fake_probability` in the
candidate dict. The same applies to brand safety (VADER / transformer
backends can replace the lexicon in `sentiment_backends.py`).

---

## 10. Run the tests

```powershell
$env:PYTHONPATH='platform;.'
python -m pytest backend.pipeline\tests tests\test_role5.py -q
```

The suite covers:

* 5 HTML fixtures (handle-only, fitness, nutrition, researcher, risky)
* Handle / URL / credential / social-URL extraction
* spaCy optional fallback
* URL normalization
* URL hash identity merge
* Fuzzy identity merge and ambiguous handoff
* Detection category classification for all 9 categories
* Per-detector fake-risk formulas
* 5-layer renormalized fusion (including all-missing case)
* Engagement quality, sentiment suppression, credibility rules
* Source confidence with and without repetition
* Trust formula with all three caps
* Final output JSON contract and event payloads
* Contact-info extraction (emails, phones, websites, addresses)
* PII redaction in public events (hashed vs. emptied modes)
* Enable/disable config flag (`ROLE5_EXTRACT_CONTACT_INFO`)

---

## 11. Contact-info extraction (PII)

`backend.pipeline/extraction/contact_info.py` adds four extractors:

| Field     | Source                                                            | Notes |
| --------- | ----------------------------------------------------------------- | ----- |
| emails    | regex with placeholder filter (`example.com`, `test.com`, etc.)  | case-insensitive dedupe |
| phones    | international regex, 7-15 digits, year-only false positive filter | preserves original formatting |
| websites  | non-social, non-placeholder URLs                                  | social-platform allowlist |
| addresses | street + city/state/zip regex + PO Box + spaCy GPE/LOC/FAC fallback | best-effort, locale-dependent |

Each mention record and the final pipeline result carry a
`contact_info` block:

```json
{
  "emails": ["sarahtan@gmail.com"],
  "phones": ["+1 415-555-0199"],
  "websites": ["https://drsarahtan.com"],
  "addresses": ["123 Market Street, San Francisco, CA 94103"],
  "enabled": true
}
```

### Configuration

| Env var                            | Default | Effect                                              |
| ---------------------------------- | ------- | --------------------------------------------------- |
| `ROLE5_EXTRACT_CONTACT_INFO`       | `1`     | When `0`, the extractor returns empty lists and the orchestrator omits `contact_info` from the final result and from the public event. |
| `ROLE5_HASH_CONTACT_IN_EVENTS`     | `1`     | When `0`, the public event's `contact_info` is emptied entirely (no hashes either). |

### Redaction guarantees

* The backend result keeps **plain-text** contact info for PostgreSQL
  storage.
* The public `score.calculated` event payload **always** carries
  redacted contact info: either SHA-256-truncated hashes (default) or
  empty lists (when `ROLE5_HASH_CONTACT_IN_EVENTS=0`).
* Plaintext PII never appears in the WebSocket event stream, the
  Redis `pipeline_events:{campaign_id}` list, or the Flower logs.
