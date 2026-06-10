# Backend Tasks Before Frontend Integration

Status: completed for the localhost hackathon flow on 2026-06-08.

This checklist captures the remaining backend work needed before the current localhost hackathon phase is integrated with the frontend.

## Current Backend Position

The backend is usable for initial frontend integration. The following endpoints and runtime pieces already exist:

- `GET /health`
- `GET /ready`
- `GET /ops/queues`
- `POST /api/campaigns`
- `GET /api/campaigns/{campaign_id}`
- `GET /api/campaigns/{campaign_id}/state`
- `GET /api/campaigns/{campaign_id}/influencers`
- `WS /ws/campaign/{campaign_id}`
- Campaign pipeline trigger
- Redis pipeline state via `pipeline_state:{campaign_id}`
- Redis event replay via `pipeline_events:{campaign_id}`
- Four Celery queues: `search_queue`, `crawl_queue`, `extract_queue`, `score_queue`

## P0: Required Before Frontend Integration

| Task | Dependency | Acceptance Criteria |
|---|---|---|
| Add CORS for `http://localhost:3000` | No blocker | Completed. Backend now allows localhost frontend origins. |
| Finalize frontend-facing campaign API contract | Coordinate with frontend field naming | Completed. Backend stays snake_case; frontend API layer maps to camelCase (`campaign_id` -> `campaignId`). |
| Align WebSocket event schema with frontend types | Backend + frontend agreement required | Completed. Frontend now uses the backend envelope: `event_id`, `type`, `campaign_id`, `timestamp`, `payload`. |
| Verify WebSocket replay during reconnect | Existing backend support needs test coverage | Completed in implementation. Frontend reconnects with `?last_event_id=N` and backend replay remains event-list based. |
| Add WebSocket heartbeat or define polling fallback | Frontend needs predictable connection UX | Completed. Backend emits heartbeat messages and frontend also polls `/state` as fallback. |

## P1: Strongly Recommended Backend Polish

| Task | Dependency | Acceptance Criteria |
|---|---|---|
| Add influencer filters | Depends on frontend filter UI choices | Completed in backend API: `platform`, `grade`, `min_followers`, `max_followers`. |
| Add influencer sort options | Depends on frontend ranking UI choices | Completed in backend API: `match_score`, `trust_grade`, `engagement_rate`, `followers`, `name`, `created_at`. |
| Return pagination metadata | No hard blocker | Completed. Influencer response now returns `items`, `total`, `limit`, `offset`, `filters`, and `sort`. |
| Improve failed/partial campaign response clarity | No hard blocker | Completed. Campaign and state responses now expose `error`, `influencer_count`, and `partial_results_available`. |
| Add demo seed/reset path | Useful for hackathon reliability | Completed. Use `scripts/seed_demo_campaign.py` to create and wait for a demo shortlist. |

## Integration Recommendation

Start frontend integration after the P0 items are complete. The safest first flow is:

1. Frontend calls `GET /health` or `GET /ready`.
2. Frontend submits `POST /api/campaigns`.
3. Frontend opens `WS /ws/campaign/{campaign_id}`.
4. Frontend polls `GET /api/campaigns/{campaign_id}/state` as fallback.
5. Frontend loads `GET /api/campaigns/{campaign_id}/influencers` when state becomes `completed`, or displays partial results if state becomes `failed`.

## Final Contract Decisions

- Backend JSON remains snake_case.
- Frontend uses a small API mapping layer and exposes camelCase to UI components.
- `GET /api/campaigns/{campaign_id}/influencers` now returns:
  - `items`
  - `total`
  - `limit`
  - `offset`
  - `filters`
  - `sort`
- WebSocket events use the backend envelope directly.
- The shortlist page uses WebSocket first and polling `/state` as fallback.

## Can Wait Until After Initial Integration

- Full Alembic migration setup.
- Authentication/API key handling.
- Multi-tenant brand scoping.
- Production deployment work.
- Advanced graph/network influencer endpoints.
- PDF/CSV export endpoints.
