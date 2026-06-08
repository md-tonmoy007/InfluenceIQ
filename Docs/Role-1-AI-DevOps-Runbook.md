# Role-1 AI-DevOps Runbook

## Current Runtime Contract

Services expected in local Docker:

- `backend-core`
- `postgres`
- `redis`
- `flower`
- `worker_search`
- `worker_crawl`
- `worker_extract`
- `worker_score`

Celery queues:

- `search_queue`
- `crawl_queue`
- `extract_queue`
- `score_queue`

Redis keys:

- `pipeline_state:{campaign_id}` stores the latest campaign state hash.
- `pipeline_events:{campaign_id}` stores replayable WebSocket events.
- `pipeline_event_seq:{campaign_id}` stores the replay event sequence counter.
- `campaign:{campaign_id}` is the live pub/sub channel.

Backend checks:

- `GET /health` checks backend dependencies and queue depths.
- `GET /ready` checks DB, Redis, and whether every expected queue has at least one visible worker.
- `GET /ops/queues` shows queue depth, worker liveness, active/reserved/scheduled tasks, and failed task counts from the Celery result backend.
- `GET /api/campaigns/{campaign_id}/state` reads `pipeline_state:{campaign_id}`.
- `GET /api/campaigns/{campaign_id}/influencers` confirms shortlist persistence.
- `WS /ws/campaign/{campaign_id}` replays `pipeline_events:{campaign_id}` and streams live updates.

## Smoke Test

Start the stack:

```powershell
docker compose up -d --build
```

Check basic health:

```powershell
curl http://localhost:8000/health
```

Run the campaign smoke test:

```powershell
python scripts/smoke_campaign.py
```

Acceptance criteria:

- `/health` reports `db=connected` and `redis=connected`.
- `/ready` reports `status=ready` and `missing_queues=[]`.
- `/ops/queues` reports all four queues with assigned workers and a visible `failed_count`.
- The smoke script creates a campaign.
- Campaign state reaches `completed`.
- Influencer results are returned by the API.
- All four queues return to depth `0`.

Queue observability:

```powershell
curl http://localhost:8000/ops/queues
```

Use this endpoint when a campaign is slow or stuck. It should show:

- `queues.*.depth`
- `queues.*.workers`
- `queues.*.active_tasks`
- `queues.*.reserved_tasks`
- `queues.*.scheduled_tasks`
- `result_backend.failed_count`
- `result_backend.status_counts`

## Troubleshooting

Worker missing:

- Run `docker compose ps`.
- Run `curl http://localhost:8000/ready`.
- Check whether `missing_queues` lists the worker's queue.
- Run `curl http://localhost:8000/ops/queues` and check which queue has no assigned workers.
- Restart only the missing worker first, for example `docker compose restart worker_score`.

Campaign stuck:

- Fetch state with `curl http://localhost:8000/api/campaigns/{campaign_id}/state`.
- Check `phase`, `last_query`, `last_url`, `scores_computed`, and `error`.
- Run `curl http://localhost:8000/ops/queues` and check queue depth plus active/reserved/scheduled task counts.
- Search logs by `campaign_id` with `docker compose logs backend-core worker_search worker_crawl worker_extract worker_score`.
- If queues are not draining, inspect `/health` queue depths and restart the owning worker.

Redis not updating:

- Confirm `/health` reports `redis=connected`.
- Check logs for `pipeline_state_write_failed` or `pipeline_event_write_failed`.
- Restart Redis only if state writes are failing and the backend cannot reconnect.

Flower not showing workers:

- Confirm `/ready` sees every expected queue.
- If `/ready` is healthy but Flower is stale, restart Flower.
- Treat transient inspect warnings during startup as non-blocking unless they continue after workers are ready.

DB unavailable:

- Confirm `/health` reports `db=connected`.
- Check `postgres` health in `docker compose ps`.
- Restart backend after Postgres becomes healthy if DB errors persist in backend logs.

## Local Failure Validation

These checks are safe for localhost hackathon development. Do not run them while another teammate is actively testing a campaign.

Missing worker:

```powershell
docker compose stop worker_score
curl http://localhost:8000/ready
curl http://localhost:8000/ops/queues
docker compose start worker_score
```

Expected result:

- `/ready` returns `status=not_ready`.
- `/ready.missing_queues` includes `score_queue`.
- `/ops/queues.queues.score_queue.workers` is empty.
- After restart, `/ready` returns `status=ready`.

DB unavailable:

```powershell
docker compose stop postgres
curl http://localhost:8000/health
curl http://localhost:8000/ready
docker compose start postgres
```

Expected result:

- `/health` returns `status=degraded` and `db=down`.
- `/ready` returns `status=not_ready` and `db=down`.
- After restart, `/ready` returns `status=ready`.

Redis unavailable:

```powershell
docker compose stop redis
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/ops/queues
docker compose start redis
```

Expected result:

- `/health` returns `status=degraded`, `redis=down`, and queue depths are `null`.
- `/ready` returns `status=not_ready` and all queues are listed in `missing_queues`.
- `/ops/queues.result_backend.connected` is `false`.
- After restart, workers reconnect and `/ready` returns `status=ready`.

## Logging Contract

Backend and worker logs are JSON-formatted through `structlog`.

Important fields:

- `campaign_id`
- `task_name`
- `phase`
- `status`
- `duration_seconds`
- `url`
- `influencer_id`

Important events:

- `campaign_created`
- `campaign_pipeline_triggered`
- `campaign_pipeline_started`
- `celery_task_dispatch_started`
- `celery_task_dispatch_completed`
- `campaign_pipeline_completed`
- `campaign_pipeline_failed`
- `queries_generated`
- `search_executed`
- `page_fetched`
- `content_extracted`
- `influencers_extracted`
- `brand_safety_classified`
- `influencer_scored`
