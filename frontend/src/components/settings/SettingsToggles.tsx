"use client";

import { useEffect, useState } from "react";
import {
  getNotificationPreferences,
  updateNotificationPreferences,
  type NotificationPreferences,
} from "@/lib/api";

type ToggleItem = {
  id: keyof Omit<NotificationPreferences, "id" | "user_id" | "updated_at">;
  title: string;
  description: string;
  defaultValue: boolean;
};

const notificationToggles: ToggleItem[] = [
  {
    id: "shortlist_ready",
    title: "Shortlist ready",
    description: "When matching finishes for a submitted brief",
    defaultValue: true,
  },
  {
    id: "creator_replied",
    title: "Creator replied",
    description: "When a contacted creator accepts or declines",
    defaultValue: true,
  },
  {
    id: "weekly_digest",
    title: "Weekly digest",
    description: "Top creators trending in your niche",
    defaultValue: false,
  },
  {
    id: "product_updates",
    title: "Product updates",
    description: "New features, occasional only",
    defaultValue: true,
  },
];

export default function SettingsToggles() {
  const [values, setValues] = useState<
    Record<ToggleItem["id"], boolean> | null
  >(null);
  // Tracks which toggle is mid-save so we can revert it on failure
  // without flickering the rest of the row.
  const [pendingId, setPendingId] = useState<ToggleItem["id"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getNotificationPreferences()
      .then((prefs) => {
        if (cancelled) return;
        setValues({
          shortlist_ready: prefs.shortlist_ready,
          creator_replied: prefs.creator_replied,
          weekly_digest: prefs.weekly_digest,
          product_updates: prefs.product_updates,
        });
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load notification preferences"
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleToggle = async (id: ToggleItem["id"]) => {
    if (values === null) return;
    const previous = values[id];
    const next = !previous;

    // Optimistic update: flip locally first, then revert on failure.
    setValues({ ...values, [id]: next });
    setPendingId(id);
    setError(null);

    try {
      const updated = await updateNotificationPreferences({
        shortlist_ready:
          id === "shortlist_ready" ? next : values.shortlist_ready,
        creator_replied:
          id === "creator_replied" ? next : values.creator_replied,
        weekly_digest: id === "weekly_digest" ? next : values.weekly_digest,
        product_updates:
          id === "product_updates" ? next : values.product_updates,
      });
      setValues({
        shortlist_ready: updated.shortlist_ready,
        creator_replied: updated.creator_replied,
        weekly_digest: updated.weekly_digest,
        product_updates: updated.product_updates,
      });
    } catch (err) {
      setValues({ ...values, [id]: previous });
      setError(
        err instanceof Error
          ? err.message
          : "Failed to update notification preference"
      );
    } finally {
      setPendingId(null);
    }
  };

  return (
    <section className="card" id="notifications">
      <h2>Notifications</h2>
      <p className="desc">
        Choose how InfluenceIQ pings you when something happens.
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
      {loading || values === null ? (
        <p
          style={{
            color: "var(--muted)",
            fontSize: "13px",
            margin: 0,
          }}
        >
          Loading notification preferences…
        </p>
      ) : (
        notificationToggles.map((t) => {
          const isOn = values[t.id];
          const isPending = pendingId === t.id;
          return (
            <div key={t.id} className="toggle-row">
              <div className="lhs">
                {t.title}
                <div className="desc">{t.description}</div>
              </div>
              <span
                className={`sw ${isOn ? "on" : ""}`}
                onClick={() => {
                  if (!isPending) void handleToggle(t.id);
                }}
                style={{
                  opacity: isPending ? 0.6 : 1,
                  cursor: isPending ? "wait" : "pointer",
                }}
                aria-label={`Toggle ${t.title}`}
                role="switch"
                aria-checked={isOn}
              ></span>
            </div>
          );
        })
      )}
    </section>
  );
}
