---
title: "InfluenceIQ: A Trust-Aware AI Platform for Influencer Discovery"
subtitle: "SciBlitz AI Challenge 2026 — Project Report"
author:
  - "Team sudo_make_it_work"
  - "Rajshahi University of Engineering & Technology (RUET)"
date: "July 8, 2026"
geometry: margin=2.2cm
fontsize: 11pt
---

**Team:** sudo_make_it_work · **Institution:** RUET · **Track:** D — Open Innovation

**Team Lead:** MD Tonmoy Hossain Jifat (tonmoyhossainjifat313@gmail.com, 01987476056)

**Members:** MD Tonmoy Hossain Jifat, Shafayetul Huda Sadi, Adib Hasan, Mahmudul Hasan

**Live demo:** https://cuet.shafayetsadi.dev/ · **Repository:** https://github.com/md-tonmoy007/InfluenceIQ

---

## 1. The Problem

Brands often choose influencers by looking at follower counts, likes, and headline reach. That is fast, but it is a weak proxy for the real question: **which creator is trustworthy enough to represent a brand and deliver real campaign value?**

This creates four common problems:

1. **Inflated influence:** fake followers, spam comments, and bot-like engagement make some creators appear stronger than they really are.
2. **Hidden risk:** a creator may have reach but still be brand-unsafe because of toxic, misleading, or low-trust content patterns.
3. **Slow research:** manually checking candidates across articles, YouTube, Instagram, TikTok, and X takes too much time.
4. **Poor auditability:** teams often cannot clearly explain later why a creator was selected or rejected.

InfluenceIQ was built to turn influencer discovery into a more evidence-based, trust-aware workflow.

## 2. Our Solution

**InfluenceIQ** is a full-stack AI-assisted influencer discovery platform. A user signs in, submits a campaign brief, and receives a ranked shortlist of creators based on trust-aware scoring rather than vanity metrics alone.

The current product supports:

- campaign brief creation and draft submission,
- asynchronous search-to-score pipeline execution,
- live progress updates through REST state and WebSocket replay,
- ranked creator shortlist and creator profile views,
- saved lists and contract/outreach tracking,
- on-demand deep-analysis reports for shortlisted creators.

Instead of scoring only popularity, the system combines:

- relevance to the campaign,
- credibility,
- engagement quality,
- audience sentiment,
- brand safety,
- source confidence.

Each result is linked to persisted source evidence and versioned scoring records, making the output more explainable and auditable.

## 3. How the AI Works

InfluenceIQ is implemented as a modular monolith with:

- `Next.js` frontend,
- `FastAPI` backend,
- `PostgreSQL` for durable product data,
- `Redis` for Celery brokering, pipeline state, and event replay,
- three Celery worker roles for async execution.

### 3.1 AI pipeline flow

The current pipeline flow is:

```text
start_campaign
  -> generate_queries
  -> execute_search
  -> fetch_page
  -> extract_content
  -> extract_influencers
  -> enrich_influencer_platforms
  -> score_influencer
  -> optional classify_brand_safety
```

This means the platform:

1. generates campaign-specific search queries,
2. discovers URLs and creator references,
3. fetches and extracts content,
4. resolves creators into canonical influencer records,
5. enriches platform-specific profile/post signals,
6. computes a trust-aware score,
7. stores the results and streams progress back to the UI.

Example flow:

A skincare brand can submit a brief asking for Bangladesh-focused creators on Instagram and YouTube. InfluenceIQ then generates campaign-specific queries, discovers public sources and creator references, enriches candidate profiles, computes trust-aware scores, and returns a shortlist with grades, evidence, and deeper report options for shortlisted creators.

### 3.2 Trust-aware scoring

The final trust score is a `0–100` score with grade bands:

- `A+` for `90–100`
- `A` for `80–89`
- `B` for `70–79`
- `C` for `60–69`
- `D` for `40–59`
- `F` for `0–39`

The current positive-score weights are:

| Sub-score          | Weight |
| ------------------ | ------ |
| Relevance          | 0.20   |
| Credibility        | 0.20   |
| Engagement quality | 0.15   |
| Sentiment          | 0.15   |
| Brand safety       | 0.15   |
| Source confidence  | 0.15   |

The pipeline then subtracts a fake-risk penalty:

`trust = positive_score - 0.5 × fake_risk`

To avoid misleadingly high scores, the implementation applies caps:

- high fake-risk caps the score at `45`
- severe brand-safety risk caps the score at `40`
- sparse evidence caps the score at `70`
- low source count also reduces confidence through a multiplier

### 3.3 Model usage

The codebase supports optional model-backed components for:

- spam/low-quality text analysis,
- toxicity detection,
- AI-generated-text likelihood,
- query planning and explanation,
- embedding-backed relevance.

However, the product is intentionally **deterministic-first**. If model backends, API keys, or optional dependencies are unavailable, the system falls back to deterministic heuristics instead of failing the campaign. This makes the product easier to run, demo, and audit.

The main innovation is therefore not simply that the project can call optional models. It is the combination of trust-aware multi-signal scoring, durable evidence storage, replayable live pipeline visibility, and model-enhanced layers on top of a stable deterministic base.

### 3.4 Deep analysis

Beyond the main shortlist pipeline, the product also supports an on-demand deep-analysis workflow for a selected creator. That flow:

1. reuses stored platform/profile/post data,
2. gathers more comment and external-signal evidence,
3. synthesizes a report,
4. then re-enqueues rescoring so richer evidence can feed back into trust output.

## 4. Demo Screenshots

Below are suggested screenshot slots from the current product flow. You can add or replace the image files manually.

![InfluenceIQ login and workspace access screen](./assets/login.png){ width=75% }

_Figure: InfluenceIQ login screen used to access the campaign workspace. Judges should notice that the project is presented as a usable product rather than a script-only demo._

![InfluenceIQ dashboard overview](./assets/dashboard.png){ width=85% }

_Figure: Dashboard view showing workspace summary, recent searches, and campaign activity. This demonstrates that campaign work is persisted and organized across sessions._

![InfluenceIQ campaign brief submission](./assets/brief-form.png){ width=85% }

_Figure: Campaign brief form where the user enters campaign context and launches the matching pipeline. Judges should notice that the system starts from a real business brief, not a hardcoded creator list._

![InfluenceIQ live pipeline progress](./assets/pipeline-progress.png){ width=85% }

_Figure: Live pipeline progress view showing asynchronous search, extraction, enrichment, and scoring updates. This highlights that the product runs as a real orchestrated workflow._

![InfluenceIQ ranked shortlist output](./assets/shortlist.png){ width=85% }

_Figure: Ranked shortlist output with trust-aware creator recommendations for a campaign. This is the main product output judges should focus on._

![InfluenceIQ creator profile view](./assets/profile.png){ width=85% }

_Figure: Creator profile page showing campaign-linked trust information, evidence, and supporting metrics. This shows how the platform explains why a creator is recommended._

![InfluenceIQ deep analysis report](./assets/deep-analysis.png){ width=85% }

_Figure: Deep-analysis report view for a shortlisted creator with richer evidence and report-level assessment. This demonstrates the second-layer review workflow beyond initial ranking._

## 5. Output

The current system produces several useful outputs:

- **ranked creator shortlist** for a campaign,
- **creator profile views** with campaign-linked trust information,
- **versioned scoring records** tied to evidence,
- **brand-safety and supporting signal outputs**,
- **saved-list and outreach workflow state**,
- **deep-analysis reports** for shortlisted creators,
- **live execution progress** through state polling and replayable WebSocket events.

From a product perspective, the key output is not just a number. It is a shortlist with persisted evidence, explainable scores, and operational workflow support.

Example compact output:

```text
Campaign: Skincare launch for Bangladesh market
Creator: Maya Rahman
Trust score: 84.6
Grade: A
Confidence: Medium
Source count: 5
Primary risks: low fake-engagement risk, no severe brand-safety flag
Why surfaced: strong relevance, credible profile signals, stable engagement quality
```

This kind of output is more useful than raw follower counts because it gives the user both a ranking and a reason.

## 6. Impact & Use Cases

InfluenceIQ is useful anywhere influencer selection must be faster, safer, and more evidence-based.

### 6.1 Practical impact

- Reduces shortlist research effort from hours of manual browsing into a guided search-to-score workflow.
- Helps teams avoid paying for inflated or low-quality influence.
- Improves confidence in creator selection by storing the reasons behind the score.
- Makes influencer evaluation more repeatable and auditable across campaigns.

### 6.2 Example use cases

- **Brand marketing teams:** shortlist creators for a new product launch.
- **Agencies:** compare candidates across many campaigns with a consistent scoring approach.
- **Startups or SMEs:** run a lightweight but more disciplined influencer research workflow.
- **Manual review before outreach:** use deep analysis to inspect a high-value creator more carefully before committing budget.

## 7. Limitations

The current codebase is functional, but several limits remain clear.

1. **Provider-dependent data depth:** Instagram, TikTok, and X enrichment quality improves significantly when the primary external providers are configured; fallback scraping is shallower.
2. **User-scoped product model:** most current workspace flows are still user-scoped rather than full organization/team collaboration.
3. **Transient replay layer:** Redis event replay is operational and TTL-based, not a permanent historical event archive.
4. **Optional model stack:** several model-backed paths are available, but the default runtime still depends mainly on deterministic logic.
5. **Limited human-review tooling:** the platform stores flags and evidence but does not yet provide a full reviewer/approver workflow.
6. **Deep analysis is targeted, not bulk:** it is currently intended for one creator at a time rather than a second-pass analysis for every ranked result.

## 8. Team & Contributions

| Member                              | Institution | Role                                                              |
| ----------------------------------- | ----------- | ----------------------------------------------------------------- |
| MD Tonmoy Hossain Jifat (Team Lead) | RUET        | Pipeline intelligence, scoring logic, trust/risk design           |
| Shafayetul Huda Sadi                | RUET        | Backend platform, orchestration, frontend integration, deployment |
| Adib Hasan                          | RUET        | Frontend implementation                                           |
| Mahmudul Hasan                      | RUET        | Scraping and scoring implementation                               |

## 9. Conclusion

InfluenceIQ addresses a real product gap: brands need help deciding **who to trust**, not only who looks popular.

The current repository now implements that idea as a working software product. It accepts campaign briefs, runs an asynchronous search-to-score pipeline, stores evidence and versioned score outputs, streams progress live to the UI, and supports deeper creator investigation when needed.

That makes it more than a concept. It is a practical trust-aware influencer discovery system with clear real-world use cases and a realistic path for future expansion. In short, InfluenceIQ helps brands move from popularity-based influencer selection to evidence-based creator trust evaluation.

---

_Repository: https://github.com/md-tonmoy007/InfluenceIQ · Live demo: https://cuet.shafayetsadi.dev/_
