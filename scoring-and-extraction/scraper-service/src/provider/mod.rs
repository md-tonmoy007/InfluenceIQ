//! Scraper provider trait + concrete adapters.
//!
//! The trait is intentionally narrow: `start_job` returns the
//! expected number of items the run will produce (the actual items
//! arrive via `ingest_webhook` in the kit). This split keeps the
//! scheduler tick cheap and means a webhook-driven provider
//! (e.g. n8n) doesn't have to re-implement long-polling.

use std::time::Duration;

use tracing::info;

mod facebook;
mod n8n_instagram;
mod x_provider;

pub use facebook::FacebookProvider;
pub use n8n_instagram::N8nInstagramProvider;
pub use x_provider::XProvider;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProviderKind {
    N8nInstagram,
    FacebookDryRun,
    XDryRun,
}

impl ProviderKind {
    pub fn for_platform(platform: &str) -> Self {
        match platform.to_ascii_lowercase().as_str() {
            "instagram" | "ig" => ProviderKind::N8nInstagram,
            "facebook" | "fb" | "meta" => ProviderKind::FacebookDryRun,
            "x" | "twitter" => ProviderKind::XDryRun,
            // Unknown platforms also fall through to a dry-run so
            // the scheduler never blocks on a misconfigured job.
            _ => ProviderKind::XDryRun,
        }
    }
}

#[async_trait::async_trait]
pub trait ScraperAdapter: Send + Sync {
    fn platform(&self) -> &'static str;
    /// Kick off a job. Returns the expected item count so the
    /// scheduler can update `ingested_count` optimistically. For
    /// webhook-driven providers, the count is a forecast from the
    /// target's profile size; actual items arrive later through
    /// `ingest_webhook`.
    async fn start_job(&self, target: &str, kind: &str) -> anyhow::Result<u32>;
}

pub struct Provider {
    kind: ProviderKind,
    dry_run: bool,
}

impl Provider {
    pub fn for_platform(platform: &str, dry_run: bool) -> Self {
        let kind = ProviderKind::for_platform(platform);
        Self { kind, dry_run }
    }

    pub async fn start_job(
        &self,
        target: &str,
        kind: &str,
        nats: Option<&async_nats::Client>,
    ) -> anyhow::Result<u32> {
        // Dispatch to the concrete adapter.
        let result = match (self.kind, self.dry_run) {
            (ProviderKind::N8nInstagram, _) => {
                N8nInstagramProvider::new(nats.cloned())
                    .start_job(target, kind)
                    .await
            }
            (ProviderKind::FacebookDryRun, _) => {
                FacebookProvider.start_job(target, kind).await
            }
            (ProviderKind::XDryRun, _) => XProvider.start_job(target, kind).await,
        };
        if let Err(ref error) = result {
            tracing::warn!(%error, kind = ?self.kind, target, "scraper adapter returned error");
        }
        result
    }
}

/// Helper: small jitter to avoid synchronized bursts across
/// concurrent adapter calls.
pub(crate) async fn brief_sleep() {
    tokio::time::sleep(Duration::from_millis(50)).await;
}

pub(crate) fn log_dispatch(provider: &str, target: &str) {
    info!(provider, target, "scraper adapter dispatched");
}
