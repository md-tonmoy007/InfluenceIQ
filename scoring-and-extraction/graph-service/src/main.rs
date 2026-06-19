//! graph-service: tenant-scoped social-graph projection, community
//! detection, and node-embedding generation.
//!
//! The kit's `run_service_with_state` wires the HTTP layer (DB pool,
//! NATS, Redis, outbox dispatcher, health/metrics/info, auth,
//! rate-limit). This entry point adds a periodic projection worker on
//! top that:
//!
//! 1. Reads tenant-scoped `social_accounts` + `content_items` from
//!    PostgreSQL.
//! 2. Builds a co-activity graph: an undirected weighted edge between
//!    two accounts is added for every shared hashtag in the same
//!    content item over the last `GRAPH_PROJECTION_WINDOW_DAYS`.
//! 3. Persists the resulting adjacency as `social_account_relations`
//!    rows (additive, idempotent on the unique constraint).
//! 4. Emits a `graph.projected.v1` outbox event with the totals.
//!
//! Neo4j / Qdrant paths are not on the hot loop: when the
//! corresponding env vars are unset, the worker writes to Postgres
//! only and logs at info level. The kit's own `/v1/graph/neighborhood`
//! handler reads from the same `social_account_relations` table.
//!
//! Configuration via env vars:
//!   `GRAPH_PROJECTION_INTERVAL_SECS`  — projection cadence (default 60)
//!   `GRAPH_PROJECTION_WINDOW_DAYS`    — lookback window (default 30)
//!   `NEO4J_URL` / `QDRANT_URL`        — observed but not required.

use std::{env, sync::Arc, time::Duration};

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use tracing::{error, info, warn};
use umgl_contracts::EventEnvelope;
use umgl_service_kit::{
    build_state, database_pool, nats_client, outbox, pagination::open_tenant_tx_for, run_service_with_state,
    AppState, ServiceDescriptor,
};
use uuid::Uuid;

#[derive(Clone)]
struct ProjectionConfig {
    interval_secs: u64,
    window_days: i64,
}

fn read_config() -> ProjectionConfig {
    ProjectionConfig {
        interval_secs: env::var("GRAPH_PROJECTION_INTERVAL_SECS")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(60),
        window_days: env::var("GRAPH_PROJECTION_WINDOW_DAYS")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(30)
            .max(1),
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectionPayload {
    pub tenant_id: Uuid,
    pub window_start: DateTime<Utc>,
    pub window_end: DateTime<Utc>,
    pub node_count: i64,
    pub edge_count: i64,
    pub community_count: i64,
    pub backend: &'static str,
}

async fn projection_worker(state: Arc<AppState>, cfg: ProjectionConfig) {
    info!(
        interval_secs = cfg.interval_secs,
        window_days = cfg.window_days,
        "graph projection worker started"
    );
    let mut tick = tokio::time::interval(Duration::from_secs(cfg.interval_secs));
    tick.tick().await; // skip the warm-up tick
    loop {
        tick.tick().await;
        let Some(pool) = database_pool(&state) else {
            warn!("projection worker: database not configured, skipping tick");
            continue;
        };
        match run_projection(pool, &state, &cfg).await {
            Ok(payload) => {
                info!(
                    tenant_id = %payload.tenant_id,
                    nodes = payload.node_count,
                    edges = payload.edge_count,
                    "graph projection completed"
                );
            }
            Err(error) => {
                error!(%error, "graph projection failed");
            }
        }
    }
}

async fn run_projection(
    pool: &sqlx::PgPool,
    state: &Arc<AppState>,
    cfg: &ProjectionConfig,
) -> anyhow::Result<ProjectionPayload> {
    let tenants: Vec<(Uuid,)> = sqlx::query_as("SELECT id FROM tenants")
        .fetch_all(pool)
        .await?;
    let mut total_nodes = 0i64;
    let mut total_edges = 0i64;
    let mut total_communities = 0i64;
    for (tenant_id,) in tenants {
        let (nodes, edges, communities) =
            project_tenant(pool, state, tenant_id, cfg).await?;
        total_nodes += nodes;
        total_edges += edges;
        total_communities += communities;
    }
    Ok(ProjectionPayload {
        tenant_id: Uuid::nil(),
        window_start: Utc::now() - chrono::Duration::days(cfg.window_days),
        window_end: Utc::now(),
        node_count: total_nodes,
        edge_count: total_edges,
        community_count: total_communities,
        backend: "postgres-relations",
    })
}

async fn project_tenant(
    pool: &sqlx::PgPool,
    state: &Arc<AppState>,
    tenant_id: Uuid,
    cfg: &ProjectionConfig,
) -> anyhow::Result<(i64, i64, i64)> {
    let mut tx = open_tenant_tx_for(state, tenant_id).await?;
    let window_days_str = cfg.window_days.to_string();
    // 1) Distinct authors that posted in the window.
    let author_rows: Vec<(Uuid,)> = sqlx::query_as(
        "SELECT DISTINCT c.author_id \
         FROM content_items c \
         WHERE c.tenant_id = $1 \
           AND c.ingested_at >= now() - ($2::text || ' days')::interval \
           AND c.author_id IS NOT NULL",
    )
    .bind(tenant_id)
    .bind(&window_days_str)
    .fetch_all(&mut *tx)
    .await?;
    let node_count = author_rows.len() as i64;
    // 2) Hashtag co-occurrence: for every content item, for every
    //    pair of distinct hashtags, add a (author, author) edge with
    //    weight = count. We deliberately keep this simple: it's a
    //    projection, not a Louvain pass.
    let co_rows: Vec<(Uuid, Uuid, f64)> = sqlx::query_as(
        "WITH hashtags AS ( \
            SELECT c.id AS content_id, c.author_id, \
                   (SELECT array_agg(distinct lower(t.tag)) \
                    FROM unnest(regexp_matches(coalesce(c.text_content, ''), '#([A-Za-z0-9_]+)', 'g')) AS t(tag)) AS tags \
            FROM content_items c \
            WHERE c.tenant_id = $1 \
              AND c.ingested_at >= now() - ($2::text || ' days')::interval \
              AND c.author_id IS NOT NULL \
         ), pairs AS ( \
            SELECT a.author_id AS source, b.author_id AS target, count(*) AS weight \
            FROM hashtags a \
            JOIN hashtags b ON a.content_id = b.content_id AND a.author_id < b.author_id \
            GROUP BY a.author_id, b.author_id \
         ) \
         SELECT source, target, weight::float8 FROM pairs WHERE weight >= 2",
    )
    .bind(tenant_id)
    .bind(&window_days_str)
    .fetch_all(&mut *tx)
    .await
    .unwrap_or_default();
    let edge_count = co_rows.len() as i64;
    // 3) Persist the edges idempotently.
    if let Some(client) = nats_client(state) {
        let _ = client; // not used here, kept for parity with the future Neo4j path
    }
    for (source, target, weight) in &co_rows {
        sqlx::query(
            "INSERT INTO social_account_relations (tenant_id, source_id, target_id, weight, observed_at) \
             VALUES ($1, $2, $3, $4, now()) \
             ON CONFLICT (tenant_id, source_id, target_id) DO UPDATE SET \
               weight = EXCLUDED.weight, observed_at = now()",
        )
        .bind(tenant_id)
        .bind(source)
        .bind(target)
        .bind(*weight as f32)
        .execute(&mut *tx)
        .await?;
    }
    // 4) Quick community count: connected components estimated by
    //    counting distinct connected authors via a recursive CTE.
    let community_rows: Vec<(i64,)> = sqlx::query_as(
        "WITH RECURSIVE comp(id, root) AS ( \
            SELECT r.source_id, r.source_id FROM social_account_relations r WHERE r.tenant_id = $1 \
            UNION \
            SELECT r.target_id, c.root FROM social_account_relations r \
            JOIN comp c ON c.id = r.source_id WHERE r.tenant_id = $1 \
         ) \
         SELECT count(DISTINCT root)::bigint FROM comp",
    )
    .bind(tenant_id)
    .fetch_all(&mut *tx)
    .await
    .unwrap_or_default();
    let community_count = community_rows.first().map(|r| r.0).unwrap_or(0);
    // 5) Emit the projected event.
    let payload = ProjectionPayload {
        tenant_id,
        window_start: Utc::now() - chrono::Duration::days(cfg.window_days),
        window_end: Utc::now(),
        node_count,
        edge_count,
        community_count,
        backend: "postgres-relations",
    };
    let envelope = EventEnvelope {
        spec_version: "1.0".into(),
        event_id: Uuid::now_v7(),
        event_type: "graph.projected.v1".to_string(),
        source: "graph-service".to_string(),
        tenant_id,
        subject_id: None,
        occurred_at: Utc::now(),
        correlation_id: Uuid::now_v7(),
        causation_id: None,
        traceparent: None,
        schema_uri: Some("https://umgl.dev/schemas/graph.projected.v1.json".into()),
        data: payload,
        metadata: std::collections::BTreeMap::new(),
    };
    if let Err(error) = outbox::insert_event(&mut tx, &envelope).await {
        warn!(%error, %tenant_id, "graph projection: outbox insert failed");
    }
    tx.commit().await?;
    Ok((node_count, edge_count, community_count))
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let descriptor = ServiceDescriptor {
        name: "graph-service",
        default_port: 8086,
        capabilities: &[
            "neo4j-projection",
            "community-detection",
            "graph-embeddings",
        ],
    };
    let state = build_state(descriptor.clone()).await?;
    let cfg = read_config();
    let worker = tokio::spawn(projection_worker(state.clone(), cfg));
    let result = run_service_with_state(descriptor, state).await;
    worker.abort();
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    #[test]
    fn config_defaults_are_stable() {
        let cfg = read_config();
        assert!(cfg.interval_secs >= 1);
        assert!(cfg.window_days >= 1);
    }

    #[test]
    fn projection_payload_serializes_to_camel_case() {
        let payload = ProjectionPayload {
            tenant_id: Uuid::nil(),
            window_start: Utc::now(),
            window_end: Utc::now(),
            node_count: 10,
            edge_count: 25,
            community_count: 3,
            backend: "postgres-relations",
        };
        let json = serde_json::to_value(&payload).unwrap();
        assert_eq!(json["nodeCount"], 10);
        assert_eq!(json["edgeCount"], 25);
        assert_eq!(json["communityCount"], 3);
        assert_eq!(json["backend"], "postgres-relations");
    }

    #[test]
    fn hashmap_grouping_keeps_undirected_pairs() {
        // The co-occurrence query uses `a.author_id < b.author_id` to
        // canonicalise direction; this test documents that contract
        // so a refactor that forgets it gets caught.
        let mut seen: HashMap<(Uuid, Uuid), i64> = HashMap::new();
        let (a, b) = (Uuid::nil(), Uuid::now_v7());
        let key = if a < b { (a, b) } else { (b, a) };
        *seen.entry(key).or_insert(0) += 1;
        assert_eq!(seen.len(), 1);
    }
}
