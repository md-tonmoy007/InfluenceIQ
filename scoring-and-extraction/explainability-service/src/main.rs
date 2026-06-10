use umgl_service_kit::{run_service, ServiceDescriptor};
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    run_service(ServiceDescriptor {
        name: "explainability-service",
        default_port: 8089,
        capabilities: &["evidence-explanations", "reasoning-trace"],
    })
    .await
}
