# Role 2: Frontend Developer

**Owner:** UI Designer (also codes)
**Architecture Sections Owned:** 3 (full frontend), 18 (client-side WebSocket consumer)

You own everything the user sees. Build against contracts and mock data so you're never blocked by backend availability.

---

## Responsibilities

- Campaign submission form (product, industry, audience, platform, budget)
- Real-time workflow visualization (WebSocket consumer, progress steps)
- Influencer recommendation dashboard (ranking, filters, trust grade badges)
- Trust score explanation panel (signal breakdown, source citations)
- Brand safety flag display with warning UI
- WebSocket reconnect handling on client side
- Responsive design (desktop demo + mobile fallback)

---

## 7-Day Todo List

### Day 1 — Setup + Mocks

- [ ] Initialize Next.js project with TailwindCSS + shadcn/ui
- [ ] Create mock data fixtures (3 campaigns, 10 influencers each)
- [ ] Create mock WebSocket event stream (TypeScript file emitting events on interval)
- [ ] Get WebSocket event JSON schema contract from Backend Engineer
- [ ] Get Influencer data model JSON contract from Scoring Engineer
- [ ] Set up routing: `/`, `/campaign/new`, `/campaign/[id]`, `/campaign/[id]/results`

### Day 2 — Campaign Submission Form

- [ ] Build campaign form with all fields (product, industry, audience, platforms, budget)
- [ ] Add form validation (Zod or react-hook-form)
- [ ] Add weight customization UI (sliders for relevance/credibility/engagement/sentiment/brand safety)
- [ ] Submit handler → POST to `/api/campaigns` → redirect to live workflow page
- [ ] Style with shadcn/ui components (Card, Input, Slider, Button)

### Day 3 — Real-Time Workflow Visualization

- [ ] Build WebSocket client hook (`useCampaignStream(campaignId)`)
- [ ] Implement reconnect logic (send `campaign_id` on reconnect for event replay)
- [ ] Build progress component showing pipeline phases:
  - Generating queries → Searching → Scraping → Extracting → Scoring → Complete
- [ ] Show live counts: URLs discovered, pages scraped, influencers found
- [ ] Handle event types: `query.generated`, `url.discovered`, `page.scraped`, `influencer.found`, `score.calculated`

### Day 4 — Influencer Dashboard

- [ ] Influencer card component: avatar, name, platform icons, trust grade badge (A+/A/B/C/D)
- [ ] Ranking list view with sort options (trust, relevance, engagement)
- [ ] Filter panel (platform, niche, region, follower size, grade)
- [ ] Connect to `GET /api/campaigns/{id}/influencers` endpoint
- [ ] Loading skeletons + empty states

### Day 5 — Trust Score Explanation Panel

- [ ] Click influencer card → modal/slideover with full breakdown
- [ ] Show each sub-score with bar visualization (relevance, credibility, engagement, sentiment, brand safety)
- [ ] Display reason list: positive signals (+) and negative signals (-)
- [ ] Show confidence level badge (High/Medium/Low) + score freshness
- [ ] Display brand safety warnings prominently with source URL citations
- [ ] Show source provenance (links to where data was extracted)

### Day 6 — Polish + Edge Cases

- [ ] Partial results banner: "Pipeline ended early — showing 8 of 12 expected influencers"
- [ ] Connection lost indicator + automatic reconnect UX
- [ ] Empty state when no influencers found
- [ ] Error toasts for API failures
- [ ] Add subtle animations (Framer Motion for card entry, progress transitions)
- [ ] Test full flow on mobile viewport

### Day 7 — Demo Prep

- [ ] Add "Demo Mode" toggle that uses pre-cached campaign data
- [ ] Polish typography, spacing, color palette
- [ ] Verify all demo scenarios render correctly
- [ ] Add loading state for the live demo trigger
- [ ] Help record demo video walkthrough
- [ ] Final QA pass on all screens

---

## Key Files You Own

```
frontend/
├── app/
│   ├── page.tsx                          (landing)
│   ├── campaign/new/page.tsx             (submission form)
│   └── campaign/[id]/page.tsx            (live workflow + results)
├── components/
│   ├── CampaignForm.tsx
│   ├── PipelineProgress.tsx
│   ├── InfluencerCard.tsx
│   ├── InfluencerDashboard.tsx
│   ├── TrustScorePanel.tsx
│   ├── BrandSafetyWarning.tsx
│   └── WeightCustomizer.tsx
├── hooks/
│   ├── useCampaignStream.ts
│   └── useInfluencers.ts
├── lib/
│   ├── api.ts
│   ├── websocket.ts
│   └── mocks/
└── types/
    ├── campaign.ts
    ├── influencer.ts
    └── events.ts
```

---

## Daily Dependencies

| Day | What You Need From Whom                                                     |
| --- | --------------------------------------------------------------------------- |
| 1   | WebSocket event schema (Backend), Influencer JSON schema (Scoring)          |
| 3   | Working WebSocket endpoint emitting mock events (Backend)                   |
| 4   | `GET /api/campaigns/{id}/influencers` returning real or mock data (Backend) |
| 5   | Trust score breakdown with reasons (Scoring)                                |
| 6   | Pre-cached demo campaign IDs (AI/DevOps Lead)                               |

---

## Phase 2 — Verification System UI

- Influencer history timeline (show score changes over time)
- Score trend charts using Recharts or Tremor
- Credential verification badges (LinkedIn-verified, certificate-verified)
- Admin dashboard for managing campaigns across multiple brands
- Export to PDF / CSV functionality

## Phase 3 — Knowledge Graph UI

- Interactive network visualization using D3 or Cytoscape.js
- Influencer relationship explorer (who cites whom, who follows whom)
- Trust propagation visualization (show how authority flows through network)
- Cluster view: group influencers by community
- Comparison view: side-by-side influencer trust profiles
