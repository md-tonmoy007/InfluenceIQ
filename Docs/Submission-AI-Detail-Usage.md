# InfluenceIQ — CloudCamp Submission: AI Detail Usage

Answers tailored to the **AI Detail Usage** tab of the CloudCamp `New Submission` form, derived from `Docs/System-architecture.md`.

---

## Prompt Usage (/10)

We use a **layered prompt architecture** mapped to each pipeline stage:

1. **Query Generation** — structured XML prompts with role definition ("You are a marketing research analyst"), few-shot examples of (campaign → queries), and chain-of-thought reasoning to break the brand brief into platform-specific search intents.
2. **Identity Resolution (Pass 3)** — a tight binary-decision prompt for low-confidence merges (0.6–0.84 fuzzy match) that forces JSON output `{"merge": bool, "reason": str}` to keep token use minimal.
3. **Brand Safety Classification** — multi-label classification prompt asking yes/no across 6 risk categories with one-sentence justifications and source citation.
4. **Trust Score Explanation** — chain-of-thought prompt over normalized sub-scores to generate the human-readable "Reasons:" panel.

All prompts are stored in a versioned prompt registry (`prompts/v1/*.xml`) so we can A/B test and roll back. Iteration approach: golden-set regression test of 50 (input → expected output) pairs runs on every prompt change.

---

## Token Optimization (/10)

Cost discipline is core because the pipeline fan-outs across hundreds of URLs per campaign:

- **Hybrid deterministic-first design**: regex, spaCy NER, and keyword blocklists run *before* any LLM call. LLMs only fire on edge cases (low-confidence identity merges, ambiguous brand-safety content).
- **Redis URL cache (48h TTL)** — repeat URLs across campaigns skip both fetch and LLM extraction.
- **Model routing** — Gemini 2.5 Flash for high-volume extraction & brand-safety classification; Kimi K2 for long-context reasoning; GPT-5-mini reserved for hardest edge cases only.
- **Prompt caching** on the static system instructions (~2k tokens) shared across brand-safety calls.
- **Structured JSON outputs** with `response_format` to eliminate retries from malformed responses.
- **Context trimming**: only the cleaned-text payload (post-BeautifulSoup) is sent to the LLM, never raw HTML.
- **Batching** extraction calls in groups of 5 pages per request where possible.

---

## LLMs / Models Used (/15)

**Selected:** ChatGPT, Gemini, DeepSeek, Kimi

**How & why we used these LLMs:**

- **Kimi K2** — primary long-context reasoning model for query generation and trust-score explanation panels. Its long context window lets us pack multiple scraped influencer pages into a single explanation pass without aggressive trimming.
- **Gemini 2.5 Flash** — cheap, fast workhorse for high-volume brand-safety multi-label classification and bulk article summarization before extraction. Best $/token for our hottest path (crawl → extract).
- **DeepSeek V4** — used for influencer entity extraction and identity-resolution Pass 3 (low-confidence merge decisions). Strong structured-JSON output at low cost.
- **OpenAI GPT-4o-mini** — second-opinion judge in our LLM-as-judge eval harness, scoring outputs from the other models to avoid same-model bias.
- **OpenAI GPT-5-mini** — escalation model for the hardest reasoning cases: ambiguous brand-safety calls, edge-case identity merges, and final trust-score narrative generation where instruction-following quality matters most.

---

## Retrieval & RAG (/12)

**Selected:** Vector Database (Qdrant), Variable / Semantic Chunking, Hybrid Search (Keyword + Vector), Rerankers

**RAG architecture details:**

**Qdrant** is our primary vector store for (a) influencer content snippets, (b) campaign briefs, and (c) authority-source articles. We use `text-embedding-3-small` (1536-d) for **dense embeddings** with **semantic chunking at ~512 tokens** bounded on paragraph breaks.

Retrieval is **three-signal hybrid**:

1. **Dense vector search** (cosine similarity over `text-embedding-3-small`) — captures semantic intent.
2. **Sparse vector search** (SPLADE-style learned sparse embeddings stored alongside dense in Qdrant) — captures rare-term/exact-keyword matches that dense embeddings miss (e.g., specific certifications, brand names, handles).
3. **BM25 keyword search** — classic lexical baseline as a third signal.

Results from all three are fused with **Reciprocal Rank Fusion (RRF)** into a top-20 candidate set, then a **BGE reranker** narrows to top-5. Niche-to-influencer matching uses this hybrid pipeline to compute the **Relevance sub-score** feeding the trust formula. Source-URL provenance is preserved on every chunk so the Trust Score Explanation Panel can cite the originating page.

---

## MCP (Model Context Protocol) Usage (/20)

Not in MVP scope. *(If we ship an "InfluenceIQ MCP" server exposing `search_influencers` / `get_trust_score` for judge demos, check the box and document endpoint counts, transports, and reuse.)*

---

## Open Source Tools & Libraries (/8)

- **FastAPI + Celery + Redis** — async task pipeline backbone with 4 specialized queues (search/crawl/extract/score).
- **Playwright** — JavaScript-rendered scraping with fingerprint randomization to survive anti-bot defenses.
- **BeautifulSoup + HTTPX** — static HTML parsing and async fetching.
- **spaCy** — deterministic NER for influencer entity extraction (cheap first pass before LLM fallback).
- **Qdrant** — vector database for dense + sparse hybrid semantic similarity search.
- **Flower** — Celery worker monitoring & queue-depth dashboard.
- **shadcn/ui + TailwindCSS** — Next.js frontend component library.

---

## Agent Frameworks & Orchestration (/7)

Custom **Celery-based agent orchestration** rather than off-the-shelf frameworks, because our workflow is a DAG of long-running I/O-bound tasks (not chat-style turn-taking). We compose `chain()` + `group()` + `chord()` primitives so search → crawl → extract → score runs as a fault-tolerant pipeline with per-stage retry policies. Each Celery worker class behaves as a specialized agent:

- **Search Agent** — 2 workers, query gen + API calls
- **Crawl Agent** — 8 workers, fetch + cache + rate-limit
- **Extract Agent** — 4 workers, NER + LLM extraction
- **Score Agent** — 2 workers, trust scoring + brand-safety LLM

A FastAPI **supervisor** dispatches and streams progress to the frontend over WebSocket.

---

## Fine-tuning / Adaptation (/5)

Not applicable for MVP. All models used zero-shot or few-shot. Fine-tuning is in our Phase 2 roadmap (LoRA adaptation of a credibility classifier on a labeled influencer-niche dataset).

---

## Evaluation & Quality Measurement (/7)

- **LLM-as-judge** with GPT-4o-mini scoring Claude outputs for brand-safety classification correctness (avoids same-model bias).
- **50-question regression set** on (campaign brief → expected influencer trust grade) golden pairs, run on every prompt/formula change.
- **RAGAS** for retrieval faithfulness and answer-relevance on the relevance-scoring pipeline.
- **Identity-resolution accuracy** tracked via a hand-labeled set of 100 duplicate clusters (precision/recall on merge decisions).
- **Score reproducibility check** — every score record stores `score_version` + `data_source_count` + `confidence_level`, so we can replay historical campaigns when the formula changes.

---

## Guardrails, Safety & Privacy (/6)

- **Output schema validation** with Pydantic on every LLM response — malformed JSON triggers a retry, not a crash.
- **Two-pass brand safety**: cheap keyword blocklist runs *before* the LLM to short-circuit obvious cases and reduce attack surface.
- **Source-URL provenance** stored alongside every flagged risk — judges and users can audit every claim.
- **PII scrubbing** on scraped content before embedding (email/phone regex strip).
- **No automatic rejection** — the system flags concerns with cited sources; brands make the final call. This avoids over-trusting LLM judgement on edge cases.
- **Rate-limit + backoff** on outbound requests respects target-site ToS.
- **Confidence-cap rule**: sub-scores backed by fewer than 3 sources are capped at 70 to prevent overconfident outputs from sparse data.

---

## Frontend AI / Visual App Builders (/5)

**Selected:** Claude Artifacts, v0 (Vercel), Cursor Composer / Agent

~60% of the UI was AI-built. **v0** scaffolded the campaign submission form and influencer dashboard cards. **Claude Artifacts** prototyped the Trust Score Explanation Panel and the real-time pipeline visualization. **Cursor Composer** handled refinement, WebSocket wiring, and shadcn/ui integration. Hand-coding focused on the WebSocket event-replay client and the score-explanation cite-source interactions.

---

## Workflow Automation (/4 + n8n bonus +2)

**Selected:** n8n (post-pipeline automation), LangGraph (optional, for scoring chain)

Our async workflow is Celery-native by design. We layer **n8n** on top for *post-pipeline* automations: e.g., when a campaign completes → generate PDF report → email it to the brand → log to CRM. This unlocks the n8n bonus and cleanly separates the hot pipeline from cold delivery side-effects.

---

## Local / On-device LLMs (/8)

Not in MVP scope. All inference runs against hosted APIs (Kimi K2, Gemini 2.5 Flash, DeepSeek V4, OpenAI GPT-4o-mini / GPT-5-mini). Local/on-device runtime is a Phase 2 consideration for PII-sensitive deployments.

---

## Build a Live /docs Module

**Yes** — we will run the `/docs` module prompt and ship a live documentation page as our live pitch deck + technical whitepaper + system dashboard.

---

## Anything else about your AI usage?

Our differentiator is **explainability**: every trust score is decomposable into normalized sub-scores, every sub-score carries source-URL provenance, every brand-safety flag cites the originating post, and every score record is versioned (formula + confidence + data-source count). This means a brand can defend a partnership decision with auditable evidence — something no follower-count platform offers.
