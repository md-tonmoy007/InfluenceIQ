use umgl_service_kit::{run_service, ServiceDescriptor};
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    run_service(ServiceDescriptor {
        name: "semantic-service",
        default_port: 8084,
        capabilities: &["semantic-routing", "model-registry"],
    })
    .await
}
