//! Facebook dry-run provider.
//!
//! Real Facebook Graph API wiring is out of scope for this
//! iteration. The adapter always returns `Ok(0)` and emits an
//! outbox event so operators can see that jobs targeting Facebook
//! are landing in the scheduler but not being executed. To switch
//! to a real adapter, replace the body of `start_job` with a
//! `reqwest` call to the Graph API (or to an n8n Facebook workflow)
//! and gate it behind the same `UMGL_SCRAPER_DRY_RUN` env var.

use super::{brief_sleep, log_dispatch, ScraperAdapter};

pub struct FacebookProvider;

#[async_trait::async_trait]
impl ScraperAdapter for FacebookProvider {
    fn platform(&self) -> &'static str {
        "facebook"
    }

    async fn start_job(&self, target: &str, _kind: &str) -> anyhow::Result<u32> {
        log_dispatch("facebook-dry-run", target);
        brief_sleep().await;
        tracing::info!(target, "facebook adapter is in dry-run mode; no items returned");
        Ok(0)
    }
}
