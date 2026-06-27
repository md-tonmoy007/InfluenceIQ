"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  createBillingPortalSession,
  createCheckoutSession,
  getSubscription,
  type BillingInterval,
  type PlanId,
  type Subscription,
} from "@/lib/api";

const PLANS: Array<{
  id: PlanId;
  name: string;
  monthlyPrice: number;
  yearlyPrice: number;
  bullets: string[];
  selfServe: boolean;
}> = [
  {
    id: "starter",
    name: "Explorer",
    monthlyPrice: 0,
    yearlyPrice: 0,
    bullets: ["5 active briefs", "Up to 200 matches", "CSV export"],
    selfServe: true,
  },
  {
    id: "pro",
    name: "Growth",
    monthlyPrice: 29,
    yearlyPrice: 23,
    bullets: [
      "Unlimited briefs",
      "Direct outreach",
      "Saved-list CRM",
      "Sentiment analytics",
    ],
    selfServe: true,
  },
  {
    id: "scale",
    name: "Scale",
    monthlyPrice: 0,
    yearlyPrice: 0,
    bullets: [
      "Everything in Growth",
      "5 seats included",
      "API access",
      "Priority support",
    ],
    selfServe: false,
  },
];

function formatPeriodEnd(value: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function PlanBillingSection() {
  const searchParams = useSearchParams();
  const [billingInterval, setBillingInterval] = useState<BillingInterval>("month");
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<"checkout" | "portal" | null>(null);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(
    null
  );

  const loadSubscription = useCallback(async () => {
    const sub = await getSubscription();
    setSubscription(sub);
    if (sub.billing_interval) {
      setBillingInterval(sub.billing_interval);
    }
    return sub;
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadSubscription()
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
  }, [loadSubscription]);

  useEffect(() => {
    const billing = searchParams.get("billing");
    if (!billing) return;

    const scrollToBilling = () => {
      const el = document.getElementById("billing");
      if (!el) return;
      const topbarHeight = 64;
      const padding = 24;
      const offset =
        el.getBoundingClientRect().top + window.scrollY - topbarHeight - padding;
      window.scrollTo({ top: offset, behavior: "smooth" });
    };

    scrollToBilling();

    if (billing === "success") {
      void loadSubscription()
        .then(() => {
          setMessage({
            type: "ok",
            text: "Subscription updated. Your plan will reflect shortly.",
          });
        })
        .catch(() => {
          setMessage({
            type: "ok",
            text: "Checkout completed. Refresh if your plan has not updated yet.",
          });
        });
    } else if (billing === "canceled") {
      setMessage({ type: "err", text: "Checkout was canceled." });
    }

    window.history.replaceState(null, "", "/settings#billing");
  }, [searchParams, loadSubscription]);

  const currentPlan = subscription?.plan ?? "starter";
  const isPaid =
    subscription?.status === "active" ||
    subscription?.status === "trialing" ||
    subscription?.status === "past_due";
  const trialEndLabel = formatPeriodEnd(subscription?.trial_end ?? null);
  const renewLabel = formatPeriodEnd(subscription?.current_period_end ?? null);

  const startCheckout = async () => {
    setBusy("checkout");
    setMessage(null);
    try {
      const { checkout_url } = await createCheckoutSession("pro", billingInterval);
      window.location.href = checkout_url;
    } catch (err) {
      setMessage({
        type: "err",
        text: err instanceof Error ? err.message : "Failed to start checkout",
      });
      setBusy(null);
    }
  };

  const openPortal = async () => {
    setBusy("portal");
    setMessage(null);
    try {
      const { portal_url } = await createBillingPortalSession();
      window.location.href = portal_url;
    } catch (err) {
      setMessage({
        type: "err",
        text: err instanceof Error ? err.message : "Failed to open billing portal",
      });
      setBusy(null);
    }
  };

  const displayPrice = (plan: (typeof PLANS)[number]) => {
    if (plan.id === "scale") return "Custom";
    if (plan.monthlyPrice === 0) return "$0";
    const amount =
      billingInterval === "year" ? plan.yearlyPrice : plan.monthlyPrice;
    return `$${amount}`;
  };

  return (
    <section className="card" id="billing">
      <h2>Plan &amp; Billing</h2>
      <p className="desc">
        {loading
          ? "Loading your current plan…"
          : isPaid
            ? `You're on ${capitalize(currentPlan)}. Manage billing or change your plan below.`
            : `You're on ${capitalize(currentPlan)}. Upgrade for unlimited briefs and direct outreach.`}
      </p>

      <div className="billing-toggle" style={{ marginBottom: "16px" }}>
        <button
          type="button"
          className={billingInterval === "month" ? "on" : ""}
          onClick={() => setBillingInterval("month")}
          disabled={busy !== null || isPaid}
        >
          Monthly
        </button>
        <button
          type="button"
          className={billingInterval === "year" ? "on" : ""}
          onClick={() => setBillingInterval("year")}
          disabled={busy !== null || isPaid}
        >
          Annual <span className="save">SAVE 20%</span>
        </button>
      </div>

      <div className="plan-grid">
        {PLANS.map((p) => {
          const isCurrent = p.id === currentPlan;
          const isScale = p.id === "scale";
          return (
            <div
              key={p.id}
              className={`plan${isCurrent ? " current" : ""}`}
              role="presentation"
              style={{ cursor: "default" }}
            >
              <h3>{p.name}</h3>
              <div className="price">
                {displayPrice(p)}
                {!isScale && p.monthlyPrice > 0 && (
                  <span className="u">/mo</span>
                )}
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
        {currentPlan === "starter" && (
          <button
            className="btn btn-primary btn-sm"
            type="button"
            onClick={() => void startCheckout()}
            disabled={busy !== null}
          >
            {busy === "checkout" ? "Redirecting…" : "Start 14-day free trial"}
          </button>
        )}
        {isPaid && (
          <button
            className="btn btn-primary btn-sm"
            type="button"
            onClick={() => void openPortal()}
            disabled={busy !== null}
          >
            {busy === "portal" ? "Opening…" : "Manage plan"}
          </button>
        )}
        <a className="btn btn-ghost btn-sm" href="mailto:sales@influenceiq.com">
          Contact sales for Scale
        </a>
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
          <span className="pic">
            {subscription?.has_payment_method ? "PRO" : "FREE"}
          </span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: "13.5px", fontWeight: 500 }}>
              {subscription?.status === "past_due"
                ? "Payment failed — update your card"
                : subscription?.status === "trialing"
                  ? "Trial active"
                  : subscription?.has_payment_method
                    ? "Growth subscription active"
                    : "No payment method on file"}
            </div>
            <div
              style={{
                fontSize: "12px",
                color: "var(--muted)",
                marginTop: "1px",
              }}
            >
              {subscription?.status === "trialing" && trialEndLabel
                ? `Trial ends ${trialEndLabel}.`
                : subscription?.status === "past_due"
                  ? "Update your payment method in the billing portal to avoid interruption."
                  : subscription?.has_payment_method && renewLabel
                    ? `Renews ${renewLabel}${
                        subscription.billing_interval === "year"
                          ? " (annual)"
                          : subscription.billing_interval === "month"
                            ? " (monthly)"
                            : ""
                      }.`
                    : "Upgrade to Growth for a 14-day trial with card on file."}
            </div>
          </div>
          {(isPaid || subscription?.has_payment_method) && (
            <button
              className="btn btn-ghost btn-sm"
              type="button"
              onClick={() => void openPortal()}
              disabled={busy !== null}
            >
              Update
            </button>
          )}
        </div>
      </div>
    </section>
  );
}

function capitalize(value: string): string {
  if (!value) return "Explorer";
  const labels: Record<string, string> = {
    starter: "Explorer",
    pro: "Growth",
    scale: "Scale",
  };
  return labels[value] ?? value.charAt(0).toUpperCase() + value.slice(1);
}
