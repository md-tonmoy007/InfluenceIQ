//! X (Twitter) dry-run provider. Same shape as Facebook.

use super::{brief_sleep, log_dispatch, ScraperAdapter};

pub struct XProvider;

#[async_trait::async_trait]
impl ScraperAdapter for XProvider {
    fn platform(&self) -> &'static str {
        "x"
    }

    async fn start_job(&self, target: &str, _kind: &str) -> anyhow::Result<u32> {
        log_dispatch("x-dry-run", target);
        brief_sleep().await;
        tracing::info!(target, "x adapter is in dry-run mode; no items returned");
        Ok(0)
    }
}
