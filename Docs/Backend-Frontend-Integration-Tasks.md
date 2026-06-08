# Backend Tasks Before Frontend Integration

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
| Add CORS for `http://localhost:3000` | No blocker | Browser frontend can call `/health`, `/api/campaigns`, `/state`, and `/influencers` without CORS errors. |
| Finalize frontend-facing campaign API contract | Coordinate with frontend field naming | Frontend knows whether to use backend snake_case fields directly or map them to camelCase; `campaign_id` vs `campaignId` is resolved. |
| Align WebSocket event schema with frontend types | Backend + frontend agreement required | Frontend event type matches backend shape: `event_id`, `type`, `campaign_id`, `timestamp`, and `payload`. |
| Verify WebSocket replay during reconnect | Existing backend support needs test coverage | If the client reconnects with `?last_event_id=N`, missed events are replayed and no duplicate/empty replay issue appears. |
| Add WebSocket heartbeat or define polling fallback | Frontend needs predictable connection UX | Long-running campaign page does not silently stall; either heartbeat messages are sent or frontend falls back to polling `/state`. |

## P1: Strongly Recommended Backend Polish

| Task | Dependency | Acceptance Criteria |
|---|---|---|
| Add influencer filters | Depends on frontend filter UI choices | `GET /api/campaigns/{id}/influencers` supports useful filters such as `platform`, `grade`, and follower range. |
| Add influencer sort options | Depends on frontend ranking UI choices | Influencers can be sorted by match score, trust grade, engagement, or other agreed fields. |
| Return pagination metadata | No hard blocker | Influencer response includes `items`, `total`, `limit`, and `offset`, or frontend explicitly accepts list-only pagination for the demo. |
| Improve failed/partial campaign response clarity | No hard blocker | Campaign response clearly exposes `status`, `error` if any, and whether partial influencer results are available. |
| Add demo seed/reset path | Useful for hackathon reliability | A script or endpoint can restore known demo campaign results quickly before presentation. |

## Integration Recommendation

Start frontend integration after the P0 items are complete. The safest first flow is:

1. Frontend calls `GET /health` or `GET /ready`.
2. Frontend submits `POST /api/campaigns`.
3. Frontend opens `WS /ws/campaign/{campaign_id}`.
4. Frontend polls `GET /api/campaigns/{campaign_id}/state` as fallback.
5. Frontend loads `GET /api/campaigns/{campaign_id}/influencers` when state becomes `completed`, or displays partial results if state becomes `failed`.

## Can Wait Until After Initial Integration

- Full Alembic migration setup.
- Authentication/API key handling.
- Multi-tenant brand scoping.
- Production deployment work.
- Advanced graph/network influencer endpoints.
- PDF/CSV export endpoints.

