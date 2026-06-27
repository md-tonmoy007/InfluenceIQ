"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  createCheckoutSession,
  getMeOptional,
  getSubscription,
  type BillingInterval,
  type Subscription,
} from "@/lib/api";
import { routes } from "@/lib/routes";

type Plan = "explorer" | "growth" | "scale";

type LandingPriceCtaProps = {
  plan: Plan;
  guestHref: string;
  guestLabel: string;
  filled?: boolean;
};

function getSelectedInterval(): BillingInterval {
  const annual = document.querySelector('#billing button.on[data-b="annual"]');
  return annual ? "year" : "month";
}

export default function LandingPriceCta({
  plan,
  guestHref,
  guestLabel,
  filled = false,
}: LandingPriceCtaProps) {
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    getMeOptional()
      .then(async (user) => {
        if (!active) return;
        if (!user) {
          setSignedIn(false);
          return;
        }
        setSignedIn(true);
        try {
          const sub = await getSubscription();
          if (active) setSubscription(sub);
        } catch {
          // Subscription unavailable — still allow checkout.
        }
      })
      .catch(() => {
        if (active) setSignedIn(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const className = `price-cta${filled ? " filled" : ""}`;
  const arrow = <span className="arr">&rarr;</span>;

  if (plan === "scale") {
    return (
      <a className={className} href="mailto:sales@influenceiq.com">
        Contact Sales {arrow}
      </a>
    );
  }

  if (signedIn !== true) {
    return (
      <Link className={className} href={guestHref}>
        {guestLabel} {arrow}
      </Link>
    );
  }

  if (plan === "explorer") {
    return (
      <Link className={className} href={routes.dashboard}>
        Go to Dashboard {arrow}
      </Link>
    );
  }

  const isPaid =
    subscription?.status === "active" || subscription?.status === "trialing";

  if (isPaid) {
    return (
      <Link className={className} href={`${routes.settings}#billing`}>
        Manage plan {arrow}
      </Link>
    );
  }

  const startCheckout = async () => {
    setBusy(true);
    try {
      const { checkout_url } = await createCheckoutSession(
        "pro",
        getSelectedInterval()
      );
      window.location.href = checkout_url;
    } catch {
      window.location.href = `${routes.settings}#billing`;
    }
  };

  return (
    <button
      type="button"
      className={className}
      onClick={() => void startCheckout()}
      disabled={busy}
    >
      {busy ? "Redirecting…" : "Start Free Trial"} {arrow}
    </button>
  );
}
