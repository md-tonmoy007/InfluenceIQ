//! scraper-service: provider-adapter-driven scrape jobs with a
//! scheduler worker.
//!
//! The kit's `run_service_with_state` wires the HTTP layer. This
//! entry point adds a scheduler worker that:
//!
//! 1. Polls `scrape_jobs` for `status='queued'` rows.
//! 2. Promotes them to `running` with a `started_at` timestamp.
//! 3. Dispatches to the right `Provider` adapter based on `platform`.
//! 4. On success marks the job `succeeded`; on failure marks it
//!    `failed` with `last_error`. Cancellation is honoured between
//!    adapters: a row whose `status='cancelled'` short-circuits.
//!
//! Real providers are implemented in the `provider` module. The
//! default provider is `n8n_instagram` (real), and Facebook/X are
//! dry-run stubs gated behind `UMGL_SCRAPER_DRY_RUN=true`. The
//! adapter for a job is selected at runtime; a job's `kind` field
//! (`fetch` vs `webhook`) decides whether the worker calls the
//! provider's `start_job` or whether it just listens for a webhook
//! callback (the `ingest_webhook` handler in the kit does the
//! bookkeeping).
//!
//! Configuration via env vars:
//!   `SCRAPER_TICK_SECS`           — scheduler poll interval (default 5)
//!   `SCRAPER_BATCH_SIZE`          — rows per tick (default 10)
//!   `N8N_WEBHOOK_URL`             — n8n Instagram webhook target
//!   `UMGL_SCRAPER_DRY_RUN`        — when "true", adapters are
//!     stubbed and no external calls are made.

use std::{env, sync::Arc, time::Duration};

use serde_json::{json, Value};
use tracing::{error, info, warn};
use umgl_contracts::EventEnvelope;
use umgl_service_kit::{
    build_state, database_pool, nats_client, outbox, pagination::open_tenant_tx_for,
    run_service_with_state, AppState, ServiceDescriptor,
};
use uuid::Uuid;

mod provider;
use provider::{Provider, ProviderKind};

#[derive(Clone)]
struct ScraperConfig {
    tick_secs: u64,
    batch_size: i64,
    dry_run: bool,
}

fn read_config() -> ScraperConfig {
    let tick_secs = env::var("SCRAPER_TICK_SECS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(5);
    let batch_size = env::var("SCRAPER_BATCH_SIZE")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(10)
        .clamp(1, 100);
    let dry_run = env::var("UMGL_SCRAPER_DRY_RUN")
        .map(|v| v == "true" || v == "1")
        .unwrap_or(false);
    ScraperConfig {
        tick_secs,
        batch_size,
        dry_run,
    }
}

async fn scheduler_worker(state: Arc<AppState>, cfg: ScraperConfig) {
    info!(
        tick_secs = cfg.tick_secs,
        batch_size = cfg.batch_size,
        dry_run = cfg.dry_run,
        "scraper scheduler worker started"
    );
    let mut tick = tokio::time::interval(Duration::from_secs(cfg.tick_secs));
    tick.tick().await; // skip the warm-up tick
    loop {
        tick.tick().await;
        let Some(pool) = database_pool(&state) else {
            warn!("scraper: database not configured, skipping tick");
            continue;
        };
        match drain_batch(pool, &state, &cfg).await {
            Ok(processed) => {
                if processed > 0 {
                    info!(processed, "scraper scheduler processed jobs");
                }
            }
            Err(error) => {
                error!(%error, "scraper scheduler failed");
            }
        }
    }
}

async fn drain_batch(
    pool: &sqlx::PgPool,
    state: &Arc<AppState>,
    cfg: &ScraperConfig,
) -> anyhow::Result<usize> {
    let queued: Vec<(Uuid, Uuid, String, String, String)> = sqlx::query_as(
        "SELECT id, tenant_id, platform, target, kind \
         FROM scrape_jobs \
         WHERE status = 'queued' \
         ORDER BY created_at ASC \
         LIMIT $1",
    )
    .bind(cfg.batch_size)
    .fetch_all(pool)
    .await?;
    let mut processed = 0usize;
    for (job_id, tenant_id, platform, target, kind) in queued {
        let mut tx = match open_tenant_tx_for(state, tenant_id).await {
            Ok(tx) => tx,
            Err(error) => {
                warn!(%error, %job_id, "scraper: open_tenant_tx failed");
                continue;
            }
        };
        let current: Option<(String,)> = sqlx::query_as(
            "SELECT status FROM scrape_jobs WHERE id = $1 AND tenant_id = $2",
        )
        .bind(job_id)
        .bind(tenant_id)
        .fetch_optional(&mut *tx)
        .await?;
        let Some((current_status,)) = current else {
            tx.commit().await.ok();
            continue;
        };
        if current_status != "queued" {
            tx.commit().await.ok();
            continue;
        }
        sqlx::query(
            "UPDATE scrape_jobs SET status = 'running', started_at = now() \
             WHERE id = $1 AND tenant_id = $2 AND status = 'queued'",
        )
        .bind(job_id)
        .bind(tenant_id)
        .execute(&mut *tx)
        .await?;
        tx.commit().await?;
        let provider = Provider::for_platform(&platform, cfg.dry_run);
        let result = provider
            .start_job(&target, &kind, nats_client(state))
            .await;
        let mut tx = open_tenant_tx_for(state, tenant_id).await?;
        match result {
            Ok(items) => {
                sqlx::query(
                    "UPDATE scrape_jobs SET status = 'succeeded', finished_at = now(), \
                        ingested_count = ingested_count + $1, last_error = NULL \
                     WHERE id = $2 AND tenant_id = $3",
                )
                .bind(items as i64)
                .bind(job_id)
                .bind(tenant_id)
                .execute(&mut *tx)
                .await?;
                emit_event(
                    &mut tx,
                    tenant_id,
                    job_id,
                    "scrape.job.succeeded.v1",
                    json!({ "jobId": job_id, "items": items, "platform": platform }),
                )
                .await;
            }
            Err(error) => {
                let error_message = error.to_string();
                sqlx::query(
                    "UPDATE scrape_jobs SET status = 'failed', finished_at = now(), \
                        last_error = $1 \
                     WHERE id = $2 AND tenant_id = $3",
                )
                .bind(&error_message)
                .bind(job_id)
                .bind(tenant_id)
                .execute(&mut *tx)
                .await?;
                emit_event(
                    &mut tx,
                    tenant_id,
                    job_id,
                    "scrape.job.failed.v1",
                    json!({ "jobId": job_id, "platform": platform, "error": error_message }),
                )
                .await;
            }
        }
        tx.commit().await?;
        processed += 1;
    }
    Ok(processed)
}

async fn emit_event(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    job_id: Uuid,
    event_type: &str,
    data: Value,
) {
    let envelope = EventEnvelope {
        spec_version: "1.0".into(),
        event_id: Uuid::now_v7(),
        event_type: event_type.to_string(),
        source: "scraper-service".to_string(),
        tenant_id,
        subject_id: Some(job_id),
        occurred_at: chrono::Utc::now(),
        correlation_id: Uuid::now_v7(),
        causation_id: None,
        traceparent: None,
        schema_uri: Some(format!("https://umgl.dev/schemas/{event_type}.json")),
        data,
        metadata: std::collections::BTreeMap::new(),
    };
    if let Err(error) = outbox::insert_event(tx, &envelope).await {
        warn!(%error, "scraper: outbox insert failed");
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let descriptor = ServiceDescriptor {
        name: "scraper-service",
        default_port: 8083,
        capabilities: &["scheduled-collection", "provider-adapters"],
    };
    let state = build_state(descriptor.clone()).await?;
    let cfg = read_config();
    let worker = tokio::spawn(scheduler_worker(state.clone(), cfg));
    let result = run_service_with_state(descriptor, state).await;
    worker.abort();
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn batch_size_is_clamped() {
        std::env::set_var("SCRAPER_BATCH_SIZE", "9999");
        let cfg = read_config();
        assert!(cfg.batch_size <= 100);
        std::env::remove_var("SCRAPER_BATCH_SIZE");
        let cfg = read_config();
        assert_eq!(cfg.batch_size, 10);
    }

    #[test]
    fn dry_run_defaults_to_false() {
        std::env::remove_var("UMGL_SCRAPER_DRY_RUN");
        let cfg = read_config();
        assert!(!cfg.dry_run);
    }

    #[test]
    fn provider_kind_resolves_by_platform() {
        assert_eq!(
            ProviderKind::for_platform("instagram"),
            ProviderKind::N8nInstagram
        );
        assert_eq!(
            ProviderKind::for_platform("facebook"),
            ProviderKind::FacebookDryRun
        );
        assert_eq!(ProviderKind::for_platform("x"), ProviderKind::XDryRun);
    }
}
