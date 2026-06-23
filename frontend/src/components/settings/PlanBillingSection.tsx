"use client";

import { useEffect, useState } from "react";
import { getSubscription, updateSubscription, type PlanId } from "@/lib/api";

const PLANS: Array<{
  id: PlanId;
  name: string;
  price: string;
  bullets: string[];
}> = [
  {
    id: "starter",
    name: "Starter",
    price: "$0",
    bullets: ["5 active briefs", "Up to 200 matches", "CSV export"],
  },
  {
    id: "pro",
    name: "Pro",
    price: "$149",
    bullets: [
      "Unlimited briefs",
      "Direct outreach",
      "Saved-list CRM",
      "Sentiment analytics",
    ],
  },
  {
    id: "scale",
    name: "Scale",
    price: "$499",
    bullets: [
      "Everything in Pro",
      "5 seats included",
      "API access",
      "Priority support",
    ],
  },
];

export default function PlanBillingSection() {
  const [currentPlan, setCurrentPlan] = useState<string>("starter");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<PlanId | null>(null);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(
    null
  );

  useEffect(() => {
    let cancelled = false;
    getSubscription()
      .then((sub) => {
        if (!cancelled) {
          // Normalise the server's free-text ``plan`` to one of our
          // three known ids so the "current" badge sticks to the
          // matching card. Unknown values still render as the active
          // plan via the free-text check below.
          setCurrentPlan(sub.plan);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setMessage({
            type: "err",
            text: err instanceof Error ? err.message : "Failed to load plan",
          });
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const switchPlan = async (plan: PlanId) => {
    if (plan === currentPlan) return;
    setBusy(plan);
    setMessage(null);
    try {
      const sub = await updateSubscription(plan);
      setCurrentPlan(sub.plan);
      setMessage({
        type: "ok",
        text: `Switched to the ${plan} plan.`,
      });
    } catch (err) {
      setMessage({
        type: "err",
        text: err instanceof Error ? err.message : "Failed to switch plan",
      });
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="card" id="billing">
      <h2>Plan &amp; Billing</h2>
      <p className="desc">
        {loading
          ? "Loading your current plan…"
          : `You're on the ${capitalize(currentPlan)}. Upgrade for unlimited briefs and direct outreach.`}
      </p>

      <div className="plan-grid">
        {PLANS.map((p) => {
          const isCurrent = p.id === currentPlan;
          return (
            <div
              key={p.id}
              className={`plan${isCurrent ? " current" : ""}`}
              onClick={() => {
                if (!isCurrent && !busy) void switchPlan(p.id);
              }}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if ((e.key === "Enter" || e.key === " ") && !isCurrent && !busy) {
                  void switchPlan(p.id);
                }
              }}
              style={{ cursor: isCurrent ? "default" : "pointer" }}
            >
              <h3>{p.name}</h3>
              <div className="price">
                {p.price}
                <span className="u">/mo</span>
              </div>
              <ul>
                {p.bullets.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
              {isCurrent && (
                <div
                  style={{
                    marginTop: "10px",
                    fontSize: "11.5px",
                    color: "var(--muted)",
                    fontFamily: "'JetBrains Mono',monospace",
                    letterSpacing: "0.06em",
                  }}
                >
                  Active plan
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div
        style={{
          marginTop: "16px",
          display: "flex",
          gap: "12px",
          flexWrap: "wrap",
        }}
      >
        <button
          className="btn btn-primary btn-sm"
          type="button"
          onClick={() => switchPlan("pro")}
          disabled={currentPlan === "pro" || busy !== null}
        >
          {busy === "pro"
            ? "Switching…"
            : currentPlan === "pro"
              ? "On Pro plan"
              : "Upgrade to Pro"}
        </button>
        <button
          className="btn btn-ghost btn-sm"
          type="button"
          onClick={() => switchPlan("scale")}
          disabled={currentPlan === "scale" || busy !== null}
        >
          Compare plans →
        </button>
      </div>

      {message && (
        <p
          className="msg"
          style={{
            marginTop: "12px",
            color: message.type === "ok" ? "var(--good)" : "var(--warn-ink)",
            fontSize: "12.5px",
          }}
        >
          {message.text}
        </p>
      )}

      <div
        style={{
          marginTop: "22px",
          paddingTop: "18px",
          borderTop: "1px solid var(--line-soft)",
        }}
      >
        <div
          style={{
            fontSize: "11.5px",
            fontFamily: "'JetBrains Mono',monospace",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--muted)",
            marginBottom: "10px",
          }}
        >
          Payment method
        </div>
        <div className="billing-card">
          <span className="pic">VISA</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: "13.5px", fontWeight: 500 }}>
              No payment method on file
            </div>
            <div
              style={{
                fontSize: "12px",
                color: "var(--muted)",
                marginTop: "1px",
              }}
            >
              Billing is a placeholder for this release — no card is
              stored, and plan switches are stub-only.
            </div>
          </div>
          <button
            className="btn btn-ghost btn-sm"
            type="button"
            disabled
            title="Card management is not wired in this release"
          >
            Update
          </button>
        </div>
      </div>
    </section>
  );
}

function capitalize(value: string): string {
  if (!value) return "Starter";
  return value.charAt(0).toUpperCase() + value.slice(1);
}
