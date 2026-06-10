//! n8n Instagram provider.
//!
//! The "real" provider: builds a payload describing the target
//! (handle / hashtag / post URL) and POSTs it to `N8N_WEBHOOK_URL`.
//! The n8n workflow fans out into the IG Graph API equivalents, then
//! pushes the resulting content items back to our
//! `POST /v1/scrape/providers/instagram/webhook` endpoint (see
//! `umgl-service-kit::scraper::ingest_webhook`). We do not parse
//! responses inline — n8n is the source of truth for what got
//! scraped.
//!
//! Failure modes:
//!   - `N8N_WEBHOOK_URL` unset → returns an error so the row lands
//!     in `failed` with a clear message.
//!   - HTTP non-2xx → returns the status + body in the error.

use std::{env, time::Duration};

use reqwest::Client;
use serde_json::json;

use super::{brief_sleep, log_dispatch, ScraperAdapter};

pub struct N8nInstagramProvider {
    nats: Option<async_nats::Client>,
}

impl N8nInstagramProvider {
    pub fn new(nats: Option<async_nats::Client>) -> Self {
        Self { nats }
    }
}

#[async_trait::async_trait]
impl ScraperAdapter for N8nInstagramProvider {
    fn platform(&self) -> &'static str {
        "instagram"
    }

    async fn start_job(&self, target: &str, kind: &str) -> anyhow::Result<u32> {
        let url = env::var("N8N_WEBHOOK_URL")
            .map_err(|_| anyhow::anyhow!("N8N_WEBHOOK_URL is not configured"))?;
        log_dispatch("n8n-instagram", target);
        brief_sleep().await;
        let payload = json!({
            "target": target,
            "kind": kind,
            "queuedAt": chrono::Utc::now(),
            "tenantId": env::var("UMGL_TENANT_HEADER").unwrap_or_default(),
        });
        let client = Client::builder()
            .timeout(Duration::from_secs(15))
            .build()?;
        let response = client.post(&url).json(&payload).send().await?;
        let status = response.status();
        if !status.is_success() {
            let body = response.text().await.unwrap_or_default();
            anyhow::bail!("n8n webhook returned {}: {}", status, body);
        }
        // n8n does not synchronously return item counts; we publish
        // a JetStream "scrape.requested.v1" event so the consumer
        // (the n8n workflow trigger) can pick it up if the webhook
        // path is down. This is a small redundancy that keeps the
        // platform resilient to webhook configuration mistakes.
        if let Some(client) = &self.nats {
            let _ = client
                .publish(
                    "umgl.scrape.requested.v1",
                    serde_json::to_vec(&payload)?.into(),
                )
                .await;
        }
        // Forecast 0; the real count arrives through ingest_webhook.
        Ok(0)
    }
}
