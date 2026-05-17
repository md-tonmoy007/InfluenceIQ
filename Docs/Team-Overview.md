# Team Work Distribution — Overview

**Project:** InfluenceIQ — AI-powered trust-aware influencer discovery platform
**Duration:** 7-day hackathon
**Team Size:** 5 members
**Reference:** [System-architecture.md](System-architecture.md)

---

## Team Roles

| # | Role | Member Focus | Owns Sections |
|---|------|--------------|---------------|
| 1 | AI Orchestration + DevOps Lead | LLM integration, Celery, Docker, monitoring | 2, 6, 14, 15, 16, 20, 21, 22 |
| 2 | Frontend Developer (UI Designer) | Next.js dashboard, WebSocket UI | 3, 18 (client-side) |
| 3 | Backend API + Database Engineer | FastAPI, PostgreSQL, WebSocket server | 4, 5, 18 (server), 19 |
| 4 | Scraping & Crawling Engineer | Playwright, rate limiting, URL cache | 7, 8, 9 |
| 5 | Extraction & Scoring Engineer | NLP, identity resolution, scoring rules | 10, 11, 12, 13 |

---

## 7-Day High-Level Timeline

```
Day 1  │ Foundation: Docker, schemas, contracts, mock data
Day 2  │ Core scaffolding done, all roles unblocked
Day 3  │ Core feature development (parallel work)
Day 4  │ Core features integrated, end-to-end skeleton runs
Day 5  │ Full integration, real data flowing
Day 6  │ Hardening, demo path locked, edge cases fixed
Day 7  │ Polish, pre-cached demo runs, presentation prep
```

---

## Critical Coordination Points

### Day 1 Contracts (must be agreed by EOD Day 1)

| Contract | Owner | Consumers |
|----------|-------|-----------|
| Redis key schema | AI/DevOps Lead | Backend, Scraping |
| WebSocket event JSON schema | Backend Engineer | Frontend, AI/DevOps |
| PostgreSQL schema | Backend Engineer | Scoring, Scraping |
| Celery task signatures | AI/DevOps Lead | Backend, Scraping, Scoring |
| Influencer data model JSON | Scoring Engineer | Backend, Frontend |

### Daily Sync (15 min, every morning)

- What's blocking you?
- What contract did you finalize yesterday?
- What contract do you need today?

---

## Risk Mitigation

| Risk | Probability | Owner | Mitigation |
|------|-------------|-------|------------|
| Instagram/YouTube bans scraper | High | Scraping Engineer | Test against real targets on Day 2, use Playwright fingerprinting from start |
| LLM cost overrun | Medium | AI/DevOps Lead | Hard token budget per task, blocklist before LLM |
| Integration takes too long | High | All | No new features after Day 5 — only fixes |
| Live demo fails | High | All | Pre-cache 2–3 demo campaigns, record backup video |
| WebSocket disconnects mid-demo | Medium | Backend Engineer | Event replay from Redis must work by Day 4 |

---

## Demo Strategy

- Pre-run 2–3 compelling campaigns on Day 6 and cache results
- Live demo triggers a fast/simple new query for real-time visibility
- Fall back to cached results if live run times out
- Show Flower dashboard during demo for system credibility

---

## Phase 2 (Post-Hackathon) — Verification System

| Role | Phase 2 Focus |
|------|---------------|
| AI/DevOps | Credential verification APIs, advanced fraud ML classifier |
| Frontend | Influencer history timeline, score trend charts |
| Backend | Audit log tables, score versioning APIs, multi-tenant support |
| Scraping | LinkedIn integration, certification scraping, deeper crawl |
| Scoring | ML-based credibility model, training data pipeline |

---

## Phase 3 (Long-term) — Knowledge Graph

| Role | Phase 3 Focus |
|------|---------------|
| AI/DevOps | Graph embedding pipelines, vector recommendation engine |
| Frontend | Network visualization, relationship explorer |
| Backend | Graph database integration (Neo4j or AGE), graph API layer |
| Scraping | Cross-platform relationship discovery, citation graph |
| Scoring | Trust propagation algorithms, authority graph scoring |

---

## File Index

- [Role 1: AI Orchestration + DevOps Lead](Role-1-AI-DevOps.md)
- [Role 2: Frontend Developer](Role-2-Frontend.md)
- [Role 3: Backend API + Database](Role-3-Backend.md)
- [Role 4: Scraping & Crawling](Role-4-Scraping.md)
- [Role 5: Extraction & Scoring](Role-5-Scoring.md)
