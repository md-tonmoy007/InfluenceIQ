# Role 5: Extraction & Scoring Engineer

**Architecture Sections Owned:** 10 (entity extraction), 11 (identity resolution), 12 (social intelligence), 13 (fake engagement detection)

You take raw scraped content and turn it into structured, deduplicated, scored influencer records. Your work feeds directly into the Trust Scoring Engine that AI/DevOps owns.

---

## Responsibilities

- Influencer entity extraction from text (regex, URL parsing, spaCy NER)
- Three-pass identity resolution (URL hash → fuzzy match → LLM)
- Fake engagement detection heuristics (bot probability formula)
- Credibility scoring rules implementation (signal → points table)
- Brand safety keyword blocklist (Pass 1 before LLM)
- Sentiment scoring on extracted comments
- Engagement quality calculation

---

## 7-Day Todo List

### Day 1 — Schema + Extraction Skeleton

- [ ] Define influencer JSON data model (publish to frontend + backend)
- [ ] Set up spaCy with `en_core_web_sm` model
- [ ] Write basic entity extraction: regex for `@handles`, URL parsing for profile links
- [ ] Create test fixtures: 5 sample HTML pages with known influencers to extract
- [ ] Get `crawl_sources` schema from Backend

### Day 2 — Entity Extraction

- [ ] Implement `extract_influencers` Celery task in `extract_queue`
- [ ] spaCy PERSON entity recognition
- [ ] Regex patterns for Instagram (`@username`), YouTube (`youtube.com/c/...`, `youtube.com/@...`)
- [ ] Pattern matching for credentials: "MD", "PhD", "Certified", professional titles
- [ ] Output structured record per influencer mention with `source_url`

### Day 3 — Identity Resolution (Passes 1 & 2)

- [ ] **Pass 1:** URL hash match — normalize and hash profile URLs, merge exact matches
- [ ] **Pass 2:** Fuzzy name + username similarity using `rapidfuzz`
  - Merge when Levenshtein ratio >= 0.85
  - Track confidence score
- [ ] Build canonical influencer record with `mentions[]` array
- [ ] Write to `influencers` table with merged identity
- [ ] Emit `identity.merged` event for WebSocket

### Day 4 — Identity Resolution (Pass 3) + Fake Engagement

- [ ] **Pass 3:** For confidence 0.6–0.84, send to LLM (call AI/DevOps's `resolve_identity_llm` task)
- [ ] Implement fake engagement detection:
  - Generic comment ratio (regex against "🔥🔥", "❤️", "amazing", "nice")
  - Engagement mismatch (followers / avg engagement ratio)
  - Spam ratio (repeat comments)
- [ ] Normalize bot probability to [0, 1]
- [ ] Engagement quality score = (1 - bot_probability) × 100

### Day 5 — Credibility Scoring

- [ ] Implement credibility rule engine (matches Section 14 scoring table):
  - +10 verified account, +15 professional title, +20 authority mention
  - +20 educational credentials, +15 positive sentiment, +10 engagement quality
  - -20 spam indicators, -25 brand safety risks
- [ ] Normalize raw credibility score to [0, 100]
- [ ] Apply confidence penalty (cap at 70 if < 3 sources)
- [ ] Hook into AI/DevOps's `score_influencer` final scoring task

### Day 6 — Brand Safety + Sentiment

- [ ] Build keyword blocklist for brand safety Pass 1 (hate speech, scam, controversial keywords)
- [ ] If keywords match → flag for LLM Pass 2 (AI/DevOps owns the LLM call)
- [ ] Sentiment analysis on extracted comments (use VADER or a small transformer)
- [ ] Aggregate sentiment per influencer, normalize to [0, 100]
- [ ] Write all sub-scores to `influencer_scores` table

### Day 7 — Demo Prep

- [ ] Tune scoring weights on demo campaigns so grades feel right (no all-A+ or all-D)
- [ ] Verify reason list generation produces explainable output
- [ ] Manual QA: do top 3 influencers in each demo campaign actually look credible?
- [ ] Help debug last-minute scoring issues
- [ ] Document scoring formula in a one-pager for judges

---

## Key Files You Own

```
backend/
├── tasks/
│   └── extract.py            (extract_influencers, deterministic portions)
├── extraction/
│   ├── entities.py           (spaCy + regex)
│   ├── credentials.py        (professional title patterns)
│   └── handles.py            (Instagram/YouTube/TikTok URL parsers)
├── identity/
│   ├── resolver.py           (3-pass orchestration)
│   ├── url_match.py          (Pass 1)
│   ├── fuzzy_match.py        (Pass 2, rapidfuzz)
│   └── canonical.py          (merge logic)
├── analysis/
│   ├── fake_engagement.py
│   ├── credibility.py
│   ├── sentiment.py
│   └── brand_safety_blocklist.py
└── scoring/
    └── sub_scores.py         (relevance, engagement, sentiment normalization)
```

---

## Daily Dependencies

| Day | What You Need From Whom |
|-----|-------------------------|
| 1 | `crawl_sources` schema (Backend), `influencers` schema (Backend) |
| 2 | Sample HTML pages with extractable content (Scraping) |
| 4 | `resolve_identity_llm` Celery task signature (AI/DevOps) |
| 5 | Final scoring task to feed into (AI/DevOps) |
| 6 | Brand safety LLM classifier task (AI/DevOps) |

---

## Influencer Data Model (You Define This)

```json
{
  "influencer_id": "uuid",
  "canonical_name": "Dr Sarah Tan",
  "platforms": {
    "instagram": "@drsarahtan",
    "youtube": "youtube.com/sarahtan"
  },
  "credentials": ["MD", "Certified Nutritionist"],
  "mentions": [
    {
      "name": "Sarah Tan MD",
      "source_url": "https://healthblog.example.com/...",
      "context": "Top 10 nutritionists to follow"
    }
  ],
  "sub_scores": {
    "relevance": 85,
    "credibility": 78,
    "engagement": 72,
    "sentiment": 80,
    "brand_safety": 95
  },
  "confidence": "High",
  "data_source_count": 7
}
```

Publish this on Day 1 to frontend + backend.

---

## Phase 2 — Verification System Scoring

- ML classifier for credibility (XGBoost on labeled training data, replacing heuristic)
- Train fake engagement detector on real bot-vs-human comment datasets
- Cross-reference claimed credentials against verified credential databases
- Score decay: penalize stale data, boost recently active creators
- Per-niche scoring models (fitness scoring weighs different signals than finance)

## Phase 3 — Knowledge Graph Scoring

- Implement PageRank-style trust propagation across influencer citation network
- Co-mention analysis: creators frequently cited together share trust
- Authority graph: identify hub influencers whose endorsements carry weight
- Embedding-based niche matching using pgvector + content embeddings
- Temporal graph: track how trust networks evolve over months
