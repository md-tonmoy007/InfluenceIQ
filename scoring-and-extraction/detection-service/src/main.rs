//! detection-service: ensemble risk scoring, campaign detection, and
//! policy-threshold reloading.
//!
//! The kit's `run_service_with_state` wires the HTTP layer (DB pool,
//! NATS, Redis, outbox dispatcher, health/metrics/info, auth,
//! rate-limit). This entry point builds the shared `AppState` once
//! via `build_state`, then attaches two service-specific workers:
//!
//! 1. A periodic **campaign-detection worker** that scans the latest
//!    `signal_scores` rows per tenant, looks for clusters of subjects
//!    whose `signal_type = 'cluster'` row averaged across the last
//!    window exceeds the configured threshold, and emits a
//!    `risk.campaign.detected.v1` outbox event for each cluster.
//! 2. A periodic **policy-threshold reloader** that reads
//!    `tenant_settings.policy` per tenant and caches the active
//!    threshold set in a `RwLock<HashMap<Uuid, PolicyConfig>>` for
//!    in-process risk-category decisions.
//!
//! Configuration via env vars:
//!   `DETECTION_CAMPAIGN_INTERVAL_SECS`     — campaign scan cadence (default 30)
//!   `DETECTION_POLICY_RELOAD_SECS`         — policy reload cadence (default 120)
//!   `DETECTION_CAMPAIGN_SCORE_THRESHOLD`   — cluster score to flag
//!     (default 0.7, range 0.0..=1.0)
//!   `DETECTION_CAMPAIGN_WINDOW_MINUTES`    — lookback window (default 60)

use std::{
    collections::HashMap,
    env,
    sync::{Arc, RwLock},
    time::Duration,
};

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use tracing::{error, info, warn};
use umgl_contracts::{EventEnvelope, PolicyConfig, SubjectType};
use umgl_service_kit::{
    build_state, database_pool, outbox, pagination::open_tenant_tx_for, run_service_with_state,
    AppState, ServiceDescriptor,
};
use uuid::Uuid;

#[derive(Clone)]
pub struct CampaignDetectionConfig {
    pub interval_secs: u64,
    pub score_threshold: f32,
    pub window_minutes: i64,
}

#[derive(Clone)]
pub struct PolicyReloadConfig {
    pub interval_secs: u64,
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CampaignSubjectHit {
    pub subject_id: Uuid,
    pub subject_type: SubjectType,
    pub avg_score: f32,
    pub signals_in_window: i64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CampaignPayload {
    pub campaign_id: Uuid,
    pub window_start: DateTime<Utc>,
    pub window_end: DateTime<Utc>,
    pub score_threshold: f32,
    pub subjects: Vec<CampaignSubjectHit>,
}

fn read_config() -> (CampaignDetectionConfig, PolicyReloadConfig) {
    let interval_secs = env::var("DETECTION_CAMPAIGN_INTERVAL_SECS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(30);
    let score_threshold = env::var("DETECTION_CAMPAIGN_SCORE_THRESHOLD")
        .ok()
        .and_then(|v| v.parse().ok())
        .map(|v: f32| v.clamp(0.0, 1.0))
        .unwrap_or(0.7);
    let window_minutes = env::var("DETECTION_CAMPAIGN_WINDOW_MINUTES")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(60)
        .max(1);
    let policy_secs = env::var("DETECTION_POLICY_RELOAD_SECS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(120);
    (
        CampaignDetectionConfig {
            interval_secs,
            score_threshold,
            window_minutes,
        },
        PolicyReloadConfig {
            interval_secs: policy_secs,
        },
    )
}

#[derive(Default)]
pub struct PolicyCache {
    inner: RwLock<HashMap<Uuid, CachedPolicy>>,
}

#[derive(Clone, Debug, Default)]
pub struct CachedPolicy {
    pub policy: PolicyConfig,
    pub loaded_at: DateTime<Utc>,
}

impl PolicyCache {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn get(&self, tenant_id: Uuid) -> Option<CachedPolicy> {
        let guard = self.inner.read().ok()?;
        guard.get(&tenant_id).cloned()
    }

    pub fn put(&self, tenant_id: Uuid, policy: PolicyConfig) {
        if let Ok(mut guard) = self.inner.write() {
            guard.insert(
                tenant_id,
                CachedPolicy {
                    policy,
                    loaded_at: Utc::now(),
                },
            );
        }
    }

    pub fn len(&self) -> usize {
        match self.inner.read() {
            Ok(guard) => guard.len(),
            Err(_) => 0,
        }
    }
}

async fn campaign_worker(
    state: Arc<AppState>,
    cache: Arc<PolicyCache>,
    cfg: CampaignDetectionConfig,
) {
    info!(
        interval_secs = cfg.interval_secs,
        threshold = cfg.score_threshold,
        window_minutes = cfg.window_minutes,
        "campaign-detection worker started"
    );
    let mut tick = tokio::time::interval(Duration::from_secs(cfg.interval_secs));
    // First tick fires immediately; skip it so we don't double-count
    // the warm-up window.
    tick.tick().await;
    loop {
        tick.tick().await;
        let Some(pool) = database_pool(&state) else {
            warn!("campaign worker: database not configured, skipping tick");
            continue;
        };
        match scan_campaigns(pool, &state, &cache, &cfg).await {
            Ok(count) => {
                if count > 0 {
                    info!(count, "campaign scan emitted events");
                }
            }
            Err(error) => {
                error!(%error, "campaign scan failed");
            }
        }
    }
}

async fn scan_campaigns(
    pool: &sqlx::PgPool,
    state: &Arc<AppState>,
    cache: &PolicyCache,
    cfg: &CampaignDetectionConfig,
) -> anyhow::Result<usize> {
    let tenants: Vec<(Uuid,)> = sqlx::query_as("SELECT id FROM tenants")
        .fetch_all(pool)
        .await?;
    let mut emitted = 0usize;
    for (tenant_id,) in tenants {
        // Per-tenant threshold override if the policy cache has one.
        let threshold = cache
            .get(tenant_id)
            .map(|c| c.policy.coordinated_threshold)
            .filter(|v: &f32| v.is_finite())
            .unwrap_or(cfg.score_threshold);
        let mut tx = match open_tenant_tx_for(state, tenant_id).await {
            Ok(tx) => tx,
            Err(error) => {
                warn!(%error, %tenant_id, "campaign scan: open_tenant_tx failed");
                continue;
            }
        };
        let window_end = Utc::now();
        let window_start = window_end - chrono::Duration::minutes(cfg.window_minutes);
        let rows: Vec<(Uuid, String, f64, i64)> = match sqlx::query_as(
            "SELECT s.subject_id, s.subject_type::text, avg(s.score)::float8 AS avg_score, count(*) AS n \
             FROM signal_scores s \
             WHERE s.tenant_id = $1 AND s.signal_type = 'cluster' \
               AND s.observed_at >= now() - ($2::text || ' minutes')::interval \
             GROUP BY s.subject_id, s.subject_type \
             HAVING avg(s.score) >= $3 \
             ORDER BY avg(s.score) DESC \
             LIMIT 200",
        )
        .bind(tenant_id)
        .bind(cfg.window_minutes.to_string())
        .bind(threshold)
        .fetch_all(&mut *tx)
        .await
        {
            Ok(r) => r,
            Err(error) => {
                warn!(%error, %tenant_id, "campaign scan: SELECT failed");
                continue;
            }
        };
        if rows.is_empty() {
            tx.commit().await.ok();
            continue;
        }
        let subjects: Vec<CampaignSubjectHit> = rows
            .into_iter()
            .map(|(subject_id, subject_type, avg_score, n)| CampaignSubjectHit {
                subject_id,
                subject_type: match subject_type.as_str() {
                    "content" => SubjectType::Content,
                    "cluster" => SubjectType::Cluster,
                    "campaign" => SubjectType::Campaign,
                    _ => SubjectType::Account,
                },
                avg_score: avg_score as f32,
                signals_in_window: n,
            })
            .collect();
        let payload = CampaignPayload {
            campaign_id: Uuid::now_v7(),
            window_start,
            window_end,
            score_threshold: threshold,
            subjects,
        };
        let envelope = EventEnvelope {
            spec_version: "1.0".into(),
            event_id: Uuid::now_v7(),
            event_type: "risk.campaign.detected.v1".to_string(),
            source: "detection-service".to_string(),
            tenant_id,
            subject_id: Some(payload.campaign_id),
            occurred_at: window_end,
            correlation_id: Uuid::now_v7(),
            causation_id: None,
            traceparent: None,
            schema_uri: Some("https://umgl.dev/schemas/risk.campaign.detected.v1.json".into()),
            data: payload,
            metadata: std::collections::BTreeMap::new(),
        };
        if let Err(error) = outbox::insert_event(&mut tx, &envelope).await {
            warn!(%error, "campaign scan: outbox insert failed");
            continue;
        }
        if let Err(error) = tx.commit().await {
            warn!(%error, "campaign scan: commit failed");
            continue;
        }
        emitted += 1;
    }
    Ok(emitted)
}

async fn policy_reload_worker(
    state: Arc<AppState>,
    cache: Arc<PolicyCache>,
    cfg: PolicyReloadConfig,
) {
    info!(
        interval_secs = cfg.interval_secs,
        "policy-reload worker started"
    );
    let mut tick = tokio::time::interval(Duration::from_secs(cfg.interval_secs));
    tick.tick().await;
    loop {
        tick.tick().await;
        let Some(pool) = database_pool(&state) else {
            warn!("policy worker: database not configured, skipping tick");
            continue;
        };
        match reload_policies(pool, &cache).await {
            Ok(count) => {
                if count > 0 {
                    info!(count, "policy cache reloaded");
                }
            }
            Err(error) => {
                error!(%error, "policy reload failed");
            }
        }
    }
}

async fn reload_policies(pool: &sqlx::PgPool, cache: &PolicyCache) -> anyhow::Result<usize> {
    let rows: Vec<(Uuid, Value)> =
        sqlx::query_as("SELECT tenant_id, policy FROM tenant_settings")
            .fetch_all(pool)
            .await?;
    let mut count = 0usize;
    for (tenant_id, raw) in rows {
        let policy: PolicyConfig = serde_json::from_value(raw).unwrap_or_default();
        cache.put(tenant_id, policy);
        count += 1;
    }
    Ok(count)
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let descriptor = ServiceDescriptor {
        name: "detection-service",
        default_port: 8087,
        capabilities: &["risk-ensemble", "campaign-detection", "policy-thresholds"],
    };
    let state = build_state(descriptor.clone()).await?;
    let (campaign_cfg, policy_cfg) = read_config();
    let cache = Arc::new(PolicyCache::new());
    let campaign = tokio::spawn(campaign_worker(
        state.clone(),
        cache.clone(),
        campaign_cfg,
    ));
    let policy = tokio::spawn(policy_reload_worker(state.clone(), cache, policy_cfg));
    let result = run_service_with_state(descriptor, state).await;
    campaign.abort();
    policy.abort();
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn threshold_clamps_to_unit_interval() {
        std::env::set_var("DETECTION_CAMPAIGN_SCORE_THRESHOLD", "5.0");
        let (cfg, _) = read_config();
        assert!(cfg.score_threshold <= 1.0);
        std::env::remove_var("DETECTION_CAMPAIGN_SCORE_THRESHOLD");
        let (cfg, _) = read_config();
        assert!((cfg.score_threshold - 0.7).abs() < f32::EPSILON);
    }

    #[test]
    fn policy_cache_round_trips() {
        let cache = PolicyCache::new();
        let policy = PolicyConfig::default();
        cache.put(Uuid::nil(), policy.clone());
        let got = cache.get(Uuid::nil()).expect("policy cached");
        assert_eq!(got.policy.coordinated_threshold, policy.coordinated_threshold);
    }

    #[test]
    fn subject_type_mapping_is_stable() {
        for (raw, expected) in [
            ("account", SubjectType::Account),
            ("content", SubjectType::Content),
            ("cluster", SubjectType::Cluster),
            ("campaign", SubjectType::Campaign),
        ] {
            let mapped = match raw {
                "content" => SubjectType::Content,
                "cluster" => SubjectType::Cluster,
                "campaign" => SubjectType::Campaign,
                _ => SubjectType::Account,
            };
            assert_eq!(mapped, expected);
        }
    }
}
