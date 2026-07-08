---
title: "InfluenceIQ — Model & Data Card"
subtitle: "SciBlitz AI Challenge 2026 — Team sudo_make_it_work (RUET)"
geometry: top=1cm,bottom=1cm,left=1.3cm,right=1.3cm
fontsize: 10pt
header-includes:
  - \usepackage[compact]{titlesec}
  - \titlespacing*{\section}{0pt}{4pt}{2pt}
  - \titlespacing*{\subsection}{0pt}{3pt}{1pt}
  - \AtBeginDocument{\small}
  - \setlength{\parskip}{1pt}
---

## 1. Datasets / Data Sources Used

InfluenceIQ does **not** use a proprietary training dataset collected by the team. The system operates primarily on **publicly available inference-time data** gathered during campaign execution.

| Source                         | What is used for                                 | Access path                                                      |
| ------------------------------ | ------------------------------------------------ | ---------------------------------------------------------------- |
| Instagram, TikTok, X (Twitter) | Creator profile/content discovery and enrichment | Apify actors when configured; public meta-tag fallback otherwise |
| YouTube                        | Creator profile/content discovery and enrichment | Public channel pages and RSS-based collection                    |
| Brave Search API               | Campaign-relevant creator discovery              | Primary search provider                                          |
| SerpAPI                        | Campaign-relevant creator discovery              | Fallback search provider                                         |
| scrape.do / direct HTTP fetch  | Article and web-page retrieval                   | Generic page fetching                                            |

**Important note:** this data is used only to compute per-campaign trust scores and reports. It is **not** used to fine-tune or retrain the models listed below. The system is designed around public creator/profile/post data rather than private user messages or private accounts.

## 2. Pre-Trained Models Used / Available in the Codebase

| Model                                                    | Provider                 | License                                 | Used for                                |
| -------------------------------------------------------- | ------------------------ | --------------------------------------- | --------------------------------------- |
| `mrm8488/bert-tiny-finetuned-sms-spam-detection`         | Hugging Face             | Apache-2.0                              | Optional spam / low-quality text backend |
| `microsoft/deberta-v3-base`                              | Microsoft / Hugging Face | MIT                                     | Optional heavier spam-text adapter available in the codebase      |
| `unitary/toxic-bert`                                     | Hugging Face             | Apache-2.0                              | Optional toxicity backend               |
| `roberta-base-openai-detector`                           | Hugging Face / OpenAI    | MIT                                     | Optional AI-generated-text likelihood backend |
| `llama3.1:8b-instruct`                                   | Meta                     | Llama 3.1 Community License             | Optional Llama-based explanation adapter available in the codebase |
| `openai/gpt-oss-20b:free` or configured OpenRouter model | OpenRouter               | Apache-2.0 for the listed default model | Query planning / optional LLM tasks     |
| `text-embedding-3-small`                                 | OpenAI via OpenRouter    | Proprietary API model                   | Optional semantic relevance embeddings  |

All model usage is **adapter-based and optional**. In the current repository, the default execution path is deterministic-first; model-backed paths are only used when the relevant flags, dependencies, and external keys are configured. This also means some listed models are better understood as **available adapters** rather than always-on runtime defaults — for example, the heavier DeBERTa spam classifier and the Llama-based explainer both exist in the codebase, but are not implied runtime defaults, and the active LLM backend may instead be selected via environment configuration (for example an OpenRouter-backed model). When a model backend is unavailable, the system falls back to deterministic heuristics instead of failing the pipeline.

## 3. Non-Model AI Logic

Not every AI-related component in InfluenceIQ is a learned model. The default live path currently relies heavily on deterministic methods for:

- brand-safety keyword/blocklist screening,
- rule-based extraction and fallback scoring,
- graph-style coordination/ring heuristics,
- confidence caps when evidence is sparse.

These components improve auditability and keep the system operational even when external model APIs are unavailable.

## 4. Known Limitations

- **Language and domain bias:** the text classifiers are general-purpose pretrained checkpoints and may underperform on non-English, code-mixed, or niche creator content.
- **AIGC-detector uncertainty:** AI-generated-text detection is only a supporting signal, not a reliable standalone verdict.
- **Provider-depth variance:** creator-data quality depends on external provider availability; fallback scraping is shallower than the primary configured provider paths.
- **Inference-only evidence limits:** the system only sees public data it can discover and fetch; hidden audience quality or private business context is outside scope.
- **Optional-model inconsistency:** several pretrained-model integrations are available in the codebase but are not part of the default runtime path unless explicitly enabled.

## 5. Ethical Considerations

- **False positives:** spam, toxicity, or risk flags may incorrectly penalize creators; therefore the platform should be treated as decision support, not an automatic exclusion engine.
- **Fairness:** general-purpose pretrained models may reflect biases from their original training data and may not treat all dialects, communities, or creator styles equally.
- **Transparency:** scores should be interpreted alongside source evidence, provenance, and reasoning rather than as opaque rankings.
- **Privacy boundary:** the system is intended to work on public creator/profile/content data only; it does not require private messages, passwords, or private audience records.

_Repository: https://github.com/md-tonmoy007/InfluenceIQ_
