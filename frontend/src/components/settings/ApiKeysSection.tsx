"use client";

import { useEffect, useState } from "react";
import {
  createApiKey,
  getApiKeys,
  revokeApiKey,
  type ApiKey,
  type ApiKeyCreated,
} from "@/lib/api";

export default function ApiKeysSection() {
  const [keys, setKeys] = useState<ApiKey[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [newKey, setNewKey] = useState<ApiKeyCreated | null>(null);
  const [copied, setCopied] = useState(false);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getApiKeys()
      .then((data) => {
        if (!cancelled) setKeys(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load API keys"
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const onCreate = async () => {
    setCreating(true);
    setError(null);
    try {
      const created = await createApiKey();
      setNewKey(created);
      setCopied(false);
      // Refresh the list (without the plaintext key).
      const list = await getApiKeys();
      setKeys(list);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create API key"
      );
    } finally {
      setCreating(false);
    }
  };

  const onRevoke = async (id: string) => {
    setRevokingId(id);
    setError(null);
    try {
      await revokeApiKey(id);
      setKeys((prev) => (prev ?? []).filter((k) => k.id !== id));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to revoke API key"
      );
    } finally {
      setRevokingId(null);
    }
  };

  const onCopy = async () => {
    if (!newKey) return;
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(newKey.key);
      }
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  const dismissBanner = () => {
    setNewKey(null);
    setCopied(false);
  };

  return (
    <section className="card" id="api-keys">
      <h2>API keys</h2>
      <p className="desc">
        Generate keys to authenticate against the InfluenceIQ API. The
        full key is shown only once at creation — copy it immediately.
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

      {newKey && (
        <div
          className="banner"
          style={{
            background: "var(--good-soft)",
            border: "1px solid color-mix(in oklab,var(--good),white 70%)",
            borderRadius: "10px",
            padding: "12px 14px",
            margin: "0 0 14px",
            display: "flex",
            alignItems: "center",
            gap: "10px",
            flexWrap: "wrap",
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: "11.5px",
                fontFamily: "'JetBrains Mono',monospace",
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                color: "var(--muted)",
                marginBottom: "4px",
              }}
            >
              New key (copy now &mdash; won&apos;t be shown again)
            </div>
            <code
              style={{
                display: "block",
                wordBreak: "break-all",
                fontSize: "12.5px",
                fontFamily: "'JetBrains Mono',monospace",
                background: "#fff",
                border: "1px solid var(--line)",
                borderRadius: "6px",
                padding: "8px 10px",
              }}
            >
              {newKey.key}
            </code>
          </div>
          <button
            className="btn btn-ghost btn-sm"
            type="button"
            onClick={() => void onCopy()}
          >
            {copied ? "Copied" : "Copy"}
          </button>
          <button
            className="btn btn-ghost btn-sm"
            type="button"
            onClick={dismissBanner}
          >
            Dismiss
          </button>
        </div>
      )}

      <div
        style={{
          display: "flex",
          gap: "10px",
          flexWrap: "wrap",
          marginBottom: keys && keys.length > 0 ? "12px" : 0,
        }}
      >
        <button
          className="btn btn-primary btn-sm"
          type="button"
          onClick={() => void onCreate()}
          disabled={creating}
        >
          {creating ? "Generating…" : "Generate API key"}
        </button>
      </div>

      {keys && keys.length > 0 && (
        <div
          style={{
            border: "1px solid var(--line)",
            borderRadius: "10px",
            overflow: "hidden",
          }}
        >
          {keys.map((k) => (
            <div
              key={k.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                padding: "10px 12px",
                borderBottom: "1px solid var(--line-soft)",
                fontSize: "13px",
              }}
            >
              <code
                style={{
                  fontFamily: "'JetBrains Mono',monospace",
                  fontSize: "12px",
                  color: "var(--ink-soft)",
                  flex: 1,
                  minWidth: 0,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {k.key_prefix}…
              </code>
              <span style={{ color: "var(--muted)", fontSize: "12px" }}>
                {new Date(k.created_at).toLocaleDateString()}
              </span>
              <button
                className="btn btn-ghost btn-sm"
                type="button"
                onClick={() => void onRevoke(k.id)}
                disabled={revokingId === k.id}
                style={{ borderColor: "var(--line)" }}
              >
                {revokingId === k.id ? "Revoking…" : "Revoke"}
              </button>
            </div>
          ))}
        </div>
      )}

      {keys && keys.length === 0 && (
        <p
          style={{
            color: "var(--muted)",
            fontSize: "12.5px",
            margin: "8px 0 0",
          }}
        >
          No active keys yet.
        </p>
      )}
    </section>
  );
}
