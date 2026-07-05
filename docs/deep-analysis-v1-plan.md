# Deep Analysis v1 for Campaign Creators

## Summary
Build this as an async, on-demand research workflow attached to a `(campaign_id, influencer_id)` pair, reusing the existing deep-analysis trigger and Celery job instead of creating a second pipeline. The v1 output is a research dossier with a clear campaign-fit recommendation, but the system should still treat social evidence as primary and external popularity signals as secondary evidence with explicit coverage and confidence.

Users click **Deep Analysis** on a creator from campaign results or shortlist, the backend queues a job, fetches the creator's recent platform content plus comments, enriches with external popularity signals, runs analysis, stores a reusable report, and returns a report page with evidence, risks, confidence, and recommendation.

## Key Changes

### Backend workflow
- Keep `POST /api/influencers/{id}/deep-analysis` as the entrypoint, but change it to:
  - first check for a recent successful run for the same `campaign_id + influencer_id`;
  - return that existing report when still fresh;
  - otherwise create a new run and enqueue work.
- Split the current `deep_analyze` task into staged internal steps:
  1. `collect_social_content`: fetch/update recent posts for supported platforms (`instagram`, `tiktok`, `youtube`, `x`) with target window `last 20 posts`.
  2. `collect_post_comments`: fetch/store up to configured comment caps per post.
  3. `collect_external_signals`: gather Google Trends and popularity/search evidence.
  4. `synthesize_report`: score and summarize all evidence into the final dossier.
- Publish richer progress events over the existing campaign websocket:
  - `deep_analysis.started`
  - `deep_analysis.social_collected`
  - `deep_analysis.comments_collected`
  - `deep_analysis.external_signals_collected`
  - `deep_analysis.report_ready`
  - `deep_analysis.failed`

### Data collection and providers
- Extend the provider layer under `backend/pipeline/content/providers` so each supported platform can return:
  - normalized profile metadata
  - recent posts
  - per-post comments
  - fetch coverage / limitations / failure reason
- Do not silently fall back from missing comments to captions-only analysis when the feature is marketed as comment analysis; store partial coverage and degrade confidence instead.
- Add a separate external-signal collector module for:
  - Google Trends interest-over-time and related-query summary for creator name + handle + topic variants
  - search visibility / popularity evidence using already-configured search-provider infrastructure where useful
  - optional public-web sentiment/reputation snippets only if they can be normalized and cited
- Normalize all evidence into a single internal research payload so report synthesis does not depend on raw provider shapes.

### Persistence and interfaces
- Extend `DeepAnalysisRun` with freshness and audit fields:
  - `requested_post_limit`
  - `requested_comment_limit`
  - `coverage_summary`
  - `report_version`
  - `cache_expires_at`
- Extend `DeepAnalysisReport.report_payload` to a stable schema with:
  - `creator_summary`
  - `campaign_fit_summary`
  - `platform_coverage`
  - `posts_analyzed`
  - `comments_analyzed`
  - `audience_signals`
  - `popularity_signals`
  - `brand_safety_signals`
  - `key_strengths`
  - `key_risks`
  - `recommendation`
  - `confidence_reasoning`
  - `citations`
- Add `GET /api/influencers/{id}/deep-analysis/latest?campaign_id=...` so the frontend can resolve "existing fresh report vs run needed" without starting work.
- Keep the current report route, but return the richer payload contract instead of the current minimal summary.

### Frontend UX
- Keep the current async trigger pattern, but change the button flow:
  - if a fresh report exists, open it immediately;
  - otherwise show "Starting / Collecting posts / Collecting comments / Gathering trends / Synthesizing".
- Upgrade the report page from a thin summary to a dossier with sections for:
  - recommendation
  - campaign fit
  - audience sentiment and authenticity
  - popularity and trend signals
  - brand safety / controversy indicators
  - evidence by platform and by post
  - coverage and confidence
- Surface partial-data states clearly:
  - "Instagram posts fetched, comments unavailable"
  - "Google Trends unavailable for this creator/topic"
  - "Only 7 posts available, confidence reduced"

## Test Plan
- Backend unit tests:
  - cache hit returns existing fresh report instead of queuing a new run
  - stale report triggers new run
  - partial provider coverage lowers confidence but still completes
  - failed external-signal collection does not fail the whole run when social evidence exists
  - no supported social URLs returns a clear failed/unsupported outcome
- Backend integration tests:
  - end-to-end run from `POST /deep-analysis` to stored report with mocked providers
  - websocket progress events emitted in the expected order
  - report payload includes citations, coverage, counts, and recommendation sections
- Frontend tests:
  - trigger opens existing report when fresh
  - trigger shows staged progress for a new run
  - report page renders partial-coverage states cleanly
  - shortlist/profile entry points both land on the same report workflow

## Assumptions and Defaults
- v1 is manual per creator, not bulk and not auto-run after campaign completion.
- v1 officially supports only Instagram, TikTok, YouTube, and X.
- Default fetch target is 20 recent posts and a bounded per-post comment sample; limits should be config-driven.
- The report is campaign-scoped even if some creator evidence can be reused; campaign-fit synthesis must remain specific to the current campaign brief.
- Fresh reports are reused for a short TTL window; users should have an explicit rerun path.
- Google Trends and other popularity signals are secondary evidence, never the sole basis for recommendation.
- Confidence must be derived from evidence quality and coverage, not only from whether the task finished.
