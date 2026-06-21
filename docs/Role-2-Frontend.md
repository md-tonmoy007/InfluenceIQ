# Role 2: Frontend

This role owns the brand-facing workflow surface in `frontend/src/`.

## Mission

Turn campaign creation, live pipeline progress, and ranked recommendations into a coherent product experience while treating backend contracts as the source of truth.

## Owns

- Next.js App Router pages and layouts in `frontend/src/app/`
- Product flows for landing, onboarding, campaign brief creation, discover, shortlist, profile, lists, and settings
- API client mapping and response normalization in `frontend/src/lib/api.ts`
- WebSocket URL construction and reconnect behavior in `frontend/src/lib/websocket.ts`
- Client-side event typing in `frontend/src/types/events.ts`
- Recommendation presentation, filters, profile rendering, and progress UI in `frontend/src/components/`

## Interfaces Consumed

- REST endpoints under `/api/campaigns`, `/api/influencers`, and health/demo routes exposed by `backend/api/routers/`
- WebSocket stream at `/ws/campaign/{campaign_id}?last_event_id=N`
- Campaign, influencer, and event schemas from `backend/api/schemas/` and the architecture doc
- Pipeline state fields such as `phase`, `urls_discovered`, `urls_processed`, `influencers_found`, and `scores_computed`

## Interfaces Produced

- Campaign submission payloads sent from the brief flow to `POST /api/campaigns`
- WebSocket reconnect requests carrying `last_event_id`
- UI state derived from canonical `pipeline_state` and replayed/live event envelopes

## Key Workflows

- Submit a campaign brief and transition the user into a live pipeline view.
- Poll and stream campaign progress without inventing alternate client-side lifecycle rules.
- Render partial results while campaigns are still running or when a terminal partial state is returned.
- Present recommendation score breakdowns, source-backed explanations, and safety warnings without mutating backend meaning.
- Fetch canonical influencer profiles on demand and keep profile views aligned to campaign-specific score data.

## Non-Goals

- Does not define scoring formulas, grade boundaries, or extraction logic.
- Does not own queue, worker, or Redis behavior.
- Does not persist alternate campaign or influencer truth outside the API contract.

## Key Files And Directories

- `frontend/src/app/`
- `frontend/src/components/briefs/`
- `frontend/src/components/discover/`
- `frontend/src/components/shortlist/`
- `frontend/src/components/profile/`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/websocket.ts`
- `frontend/src/types/campaign.ts`
- `frontend/src/types/influencer.ts`
- `frontend/src/types/events.ts`

## Handoff Contracts

- From Backend API + Data:
  - REST payload shapes must remain stable or versioned.
  - The WebSocket event envelope must match replay and live delivery.
- From Platform + Orchestration:
  - Connection and replay behavior must preserve `last_event_id` semantics.
- From Pipeline Intelligence:
  - Score explanations, provenance fields, and safety warnings must remain attributable and machine-readable.
