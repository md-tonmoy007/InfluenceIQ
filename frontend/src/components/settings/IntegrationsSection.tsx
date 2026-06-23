"use client";

import { useEffect, useState } from "react";
import {
  connectIntegration,
  disconnectIntegration,
  getIntegrations,
  type IntegrationProvider,
  type IntegrationStatus,
} from "@/lib/api";

const PROVIDERS: Array<{
  id: IntegrationProvider;
  label: string;
}> = [
  { id: "slack", label: "Connect Slack" },
  { id: "hubspot", label: "Connect HubSpot" },
];

export default function IntegrationsSection() {
  const [items, setItems] = useState<IntegrationStatus[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<IntegrationProvider | null>(null);

  useEffect(() => {
    let cancelled = false;
    getIntegrations()
      .then((data) => {
        if (!cancelled) setItems(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load integrations"
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const statusFor = (provider: IntegrationProvider): IntegrationStatus | undefined =>
    items?.find((i) => i.provider === provider);

  const toggle = async (provider: IntegrationProvider) => {
    const current = statusFor(provider);
    if (!current || busy) return;
    setBusy(provider);
    setError(null);
    try {
      const updated = current.connected
        ? await disconnectIntegration(provider)
        : await connectIntegration(provider);
      setItems(
        (items ?? []).map((i) =>
          i.provider === provider ? updated : i
        )
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to update integration"
      );
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="card" id="api">
      <h2>API &amp; Integrations</h2>
      <p className="desc">
        Connect InfluenceIQ to your campaign stack. Slack and HubSpot
        connections are stored in our database only — no real OAuth
        handshake is performed in this release.
      </p>
      {error && (
        <p
          className="msg"
          style={{
            color: "var(--warn-ink)",
            fontSize: "12.5px",
            margin: "0 0 10px",
          }}
        >
          {error}
        </p>
      )}
      <div
        style={{
          display: "flex",
          gap: "10px",
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        {PROVIDERS.map((p) => {
          const status = statusFor(p.id);
          const connected = status?.connected ?? false;
          const isBusy = busy === p.id;
          return (
            <button
              key={p.id}
              className="btn btn-ghost btn-sm"
              type="button"
              onClick={() => void toggle(p.id)}
              disabled={isBusy || items === null}
              style={{
                borderColor: connected
                  ? "color-mix(in oklab,var(--good),white 60%)"
                  : undefined,
                color: connected ? "var(--good)" : undefined,
              }}
            >
              {isBusy
                ? "Working…"
                : connected
                  ? `${capitalize(p.id)} connected`
                  : p.label}
            </button>
          );
        })}
      </div>
      {items && (
        <p
          style={{
            color: "var(--muted)",
            fontSize: "12px",
            margin: "14px 0 0",
          }}
        >
          {items
            .filter((i) => i.connected_at)
            .map(
              (i) =>
                `${capitalize(i.provider)} connected ${
                  i.connected_at
                    ? new Date(i.connected_at).toLocaleDateString()
                    : ""
                }`
            )
            .join(" · ") || "No integrations connected yet."}
        </p>
      )}
    </section>
  );
}

function capitalize(value: string): string {
  if (!value) return value;
  return value.charAt(0).toUpperCase() + value.slice(1);
}
