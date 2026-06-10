use umgl_service_kit::{run_service, ServiceDescriptor};
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    run_service(ServiceDescriptor {
        name: "ingestion-service",
        default_port: 8082,
        capabilities: &["webhooks", "normalization", "outbox"],
    })
    .await
}
