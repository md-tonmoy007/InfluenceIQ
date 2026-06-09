use umgl_service_kit::{run_service, ServiceDescriptor};
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    run_service(ServiceDescriptor {
        name: "behavioral-service",
        default_port: 8085,
        capabilities: &["feature-windows", "behavior-scoring"],
    })
    .await
}
