"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getOnboarding, submitOnboarding, type OnboardingPayload } from "@/lib/api";
import {
  BUDGET_MAX,
  BUDGET_MIN,
  CAMPAIGN_GOAL_OPTIONS,
  CATEGORY_OPTIONS,
  COMPANY_SIZE_OPTIONS,
  COUNTRY_OPTIONS,
  DEFAULT_MONTHLY_BUDGET,
  PLATFORM_OPTIONS,
  normalizeCategory,
} from "@/lib/brandProfile";

const PLATFORM_ICON_STYLES: Record<
  string,
  { background: React.CSSProperties; icon: React.ReactNode }
> = {
  instagram: {
    background: {
      background:
        "linear-gradient(135deg,#f58529,#dd2a7b 50%,#8134af 80%,#515bd4)",
    },
    icon: (
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="white" strokeWidth="2">
        <rect x="3" y="3" width="18" height="18" rx="5" />
        <circle cx="12" cy="12" r="4" />
        <circle cx="17.5" cy="6.5" r="0.5" fill="white" />
      </svg>
    ),
  },
  tiktok: {
    background: { background: "#0a0b10" },
    icon: (
      <svg viewBox="0 0 20 22" width="14" height="14" fill="white">
        <path d="M14.5 1c.4 1.8 1.5 3.4 3 4.4 1.1.7 2.5 1.1 3.9 1.1V11c-1.6 0-3.2-.4-4.6-1.1-.6-.3-1.2-.7-1.7-1.1v6.6c0 4.1-3.4 7.5-7.5 7.5-1.6 0-3.1-.5-4.3-1.4-1.9-1.4-3.2-3.7-3.2-6.2 0-4.1 3.4-7.5 7.5-7.5.4 0 .9 0 1.3.1v4.4c-.4-.1-.8-.2-1.3-.2-1.7 0-3.1 1.4-3.1 3.1s1.4 3.2 3.2 3.2 3.2-1.4 3.2-3.1V1h3.6z" />
      </svg>
    ),
  },
  youtube: {
    background: { background: "#ff0033" },
    icon: (
      <svg viewBox="0 0 24 18" width="16" height="12" fill="white">
        <path d="M23.5 3.5a3 3 0 0 0-2.1-2.1C19.5 1 12 1 12 1s-7.5 0-9.4.4A3 3 0 0 0 .5 3.5C.1 5.4.1 9 .1 9s0 3.6.4 5.5a3 3 0 0 0 2.1 2.1C4.5 17 12 17 12 17s7.5 0 9.4-.4a3 3 0 0 0 2.1-2.1c.4-1.9.4-5.5.4-5.5s0-3.6-.4-5.5zM9.5 12.5v-7L15.5 9l-6 3.5z" />
      </svg>
    ),
  },
  facebook: {
    background: { background: "#1877f2" },
    icon: (
      <svg viewBox="0 0 24 24" width="14" height="14" fill="white">
        <path d="M14 9V7c0-1 .5-2 2-2h2V1h-3c-3 0-5 2-5 5v3H7v4h3v9h4v-9h3l1-4h-4z" />
      </svg>
    ),
  },
};

export default function OnboardingStepper() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [brandName, setBrandName] = useState("");
  const [industry, setIndustry] = useState<string>(CATEGORY_OPTIONS[1]);
  const [companySize, setCompanySize] = useState<string>(COMPANY_SIZE_OPTIONS[1]);
  const [country, setCountry] = useState<string>(COUNTRY_OPTIONS[1]);
  const [goals, setGoals] = useState<string[]>([]);
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [budget, setBudget] = useState(DEFAULT_MONTHLY_BUDGET);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getOnboarding()
      .then((profile) => {
        if (cancelled) return;
        setBrandName(profile.brand_name);
        if (profile.industry) setIndustry(normalizeCategory(profile.industry));
        if (profile.company_size) setCompanySize(profile.company_size);
        if (profile.country) setCountry(profile.country);
        if (profile.goals?.length) setGoals(profile.goals);
        if (profile.platforms?.length) setPlatforms(profile.platforms);
        if (profile.monthly_budget != null) setBudget(profile.monthly_budget);
      })
      .catch(() => {
        // No saved profile yet — keep blank defaults.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const go = (s: number) => {
    setStep(s);
    window.scrollTo({ top: 0 });
  };

  const toggleGoal = (g: string) => {
    setGoals((prev) =>
      prev.includes(g) ? prev.filter((x) => x !== g) : [...prev, g]
    );
  };

  const togglePlatform = (p: string) => {
    setPlatforms((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  };

  const handleBudgetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setBudget(parseInt(e.target.value, 10));
  };

  type SaveStep = 1 | 2 | 3;

  const buildPayload = (saveStep: SaveStep): OnboardingPayload => {
    const payload: OnboardingPayload = {
      brand_name: brandName.trim() || "Untitled brand",
      industry: normalizeCategory(industry),
      company_size: companySize,
      country,
    };
    if (saveStep >= 2) {
      payload.goals = goals;
    }
    if (saveStep >= 3) {
      payload.platforms = platforms;
      payload.monthly_budget = budget;
    }
    return payload;
  };

  const saveProgress = async (saveStep: SaveStep) => {
    setError(null);
    await submitOnboarding(buildPayload(saveStep));
  };

  const advanceFromStep = async (fromStep: SaveStep, nextStep: number) => {
    setSubmitting(true);
    setError(null);
    try {
      await saveProgress(fromStep);
      go(nextStep);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to save onboarding details"
      );
    } finally {
      setSubmitting(false);
    }
  };

  const finish = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await saveProgress(3);
      router.push("/dashboard?welcome=1");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save onboarding details");
      setSubmitting(false);
    }
  };

  const skip = async () => {
    // Best-effort: persist whatever was filled in so far, but don't block
    // the user from leaving onboarding if the save fails.
    try {
      const saveStep: SaveStep = step >= 3 ? 3 : step >= 2 ? 2 : 1;
      await saveProgress(saveStep);
    } catch {
      // ignored — skipping should never get stuck on a network error
    }
    router.push("/dashboard?welcome=1");
  };

  const budgetPct = ((budget - BUDGET_MIN) / (BUDGET_MAX - BUDGET_MIN)) * 100;

  return (
    <div className="wrap">
      <div className="top">
        <Link className="brand" href="/">
          <span className="brand-mark">i</span>
          <span>InfluenceIQ</span>
        </Link>
        <div className="progress" id="progress">
          <div
            className={`step-dot ${step === 1 ? "active" : ""} ${
              step > 1 ? "done" : ""
            }`}
            onClick={() => go(1)}
            style={{ cursor: "pointer" }}
          >
            <span className="num">1</span>
            <span className="step-label">Your brand</span>
          </div>
          <div className={`bar ${step > 1 ? "done" : ""}`}></div>
          <div
            className={`step-dot ${step === 2 ? "active" : ""} ${
              step > 2 ? "done" : ""
            }`}
            onClick={() => go(2)}
            style={{ cursor: "pointer" }}
          >
            <span className="num">2</span>
            <span className="step-label">Goals</span>
          </div>
          <div className={`bar ${step > 2 ? "done" : ""}`}></div>
          <div
            className={`step-dot ${step === 3 ? "active" : ""}`}
            onClick={() => go(3)}
            style={{ cursor: "pointer" }}
          >
            <span className="num">3</span>
            <span className="step-label">Platforms</span>
          </div>
        </div>
        <button className="quit" onClick={skip} disabled={submitting}>
          Skip for now
        </button>
      </div>

      <div className="body">
        <div className="card">
          {/* STEP 1 */}
          <section className={`step-view ${step === 1 ? "active" : ""}`} id="s1">
            <span className="eyebrow">Step 1 of 3</span>
            <h1>
              Tell us about your <span className="ac">brand.</span>
            </h1>
            <p className="sub">
              We use this to calibrate match scoring and surface creators whose
              audiences fit yours.
            </p>
            <div className="field">
              <label>Brand name</label>
              <input
                value={brandName}
                onChange={(e) => setBrandName(e.target.value)}
              />
            </div>
            <div className="grid2">
              <div className="field">
                <label>Industry</label>
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                >
                  {CATEGORY_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Company size</label>
                <select
                  value={companySize}
                  onChange={(e) => setCompanySize(e.target.value)}
                >
                  {COMPANY_SIZE_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="field">
              <label>Country</label>
              <select
                value={country}
                onChange={(e) => setCountry(e.target.value)}
              >
                {COUNTRY_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
            <div className="actions">
              <span></span>
              <button
                className="next"
                onClick={() => advanceFromStep(1, 2)}
                disabled={submitting}
              >
                {submitting ? "Saving…" : "Next"}
                {!submitting && (
                  <span
                    style={{
                      fontFamily: "Instrument Serif, serif",
                      fontStyle: "italic",
                    }}
                  >
                    →
                  </span>
                )}
              </button>
            </div>
            {error && step === 1 && <p className="error">{error}</p>}
          </section>

          {/* STEP 2 */}
          <section className={`step-view ${step === 2 ? "active" : ""}`} id="s2">
            <span className="eyebrow">Step 2 of 3</span>
            <h1>
              What are your <span className="ac">campaign goals?</span>
            </h1>
            <p className="sub">
              Pick as many as apply. We&apos;ll prioritise creators with proven
              outcomes against these.
            </p>
            <div className="chips" id="goals">
              {CAMPAIGN_GOAL_OPTIONS.map((goal) => (
                <span
                  key={goal.id}
                  className={`gchip ${goals.includes(goal.id) ? "on" : ""}`}
                  onClick={() => toggleGoal(goal.id)}
                >
                  {goal.label}{" "}
                  <span className="check">
                    <svg viewBox="0 0 16 12">
                      <path
                        d="M1 6 L6 11 L15 1"
                        stroke="white"
                        strokeWidth="2.4"
                        fill="none"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                </span>
              ))}
            </div>
            <div className="actions">
              <button className="back" onClick={() => go(1)} disabled={submitting}>
                ← Back
              </button>
              <button
                className="next"
                onClick={() => advanceFromStep(2, 3)}
                disabled={submitting}
              >
                {submitting ? "Saving…" : "Next"}
                {!submitting && (
                  <span
                    style={{
                      fontFamily: "Instrument Serif, serif",
                      fontStyle: "italic",
                    }}
                  >
                    →
                  </span>
                )}
              </button>
            </div>
            {error && step === 2 && <p className="error">{error}</p>}
          </section>

          {/* STEP 3 */}
          <section className={`step-view ${step === 3 ? "active" : ""}`} id="s3">
            <span className="eyebrow">Step 3 of 3</span>
            <h1>
              Which platforms do you <span className="ac">focus on?</span>
            </h1>
            <p className="sub">
              Toggle the platforms you care about and set a typical monthly
              budget.
            </p>
            <div className="pgrid" id="platforms">
              {PLATFORM_OPTIONS.map((platform) => (
                <div
                  key={platform.id}
                  className={`pcard ${platforms.includes(platform.id) ? "on" : ""}`}
                  onClick={() => togglePlatform(platform.id)}
                >
                  <span
                    className="icon"
                    style={PLATFORM_ICON_STYLES[platform.id].background}
                  >
                    {PLATFORM_ICON_STYLES[platform.id].icon}
                  </span>
                  <div>
                    <div className="nm">{platform.label}</div>
                    <div className="desc">{platform.desc}</div>
                  </div>
                  <span className="tick">
                    <svg viewBox="0 0 16 12">
                      <path
                        d="M1 6 L6 11 L15 1"
                        stroke="white"
                        strokeWidth="2.4"
                        fill="none"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                </div>
              ))}
            </div>

            <div className="budget-box">
              <div className="budget-head">
                <div className="l">Monthly budget</div>
                <div className="v">
                  $<span id="bv">{budget.toLocaleString()}</span>
                  <span className="u">/mo</span>
                </div>
              </div>
              <div className="slider">
                <div
                  className="fill"
                  id="fill"
                  style={{ width: `${budgetPct}%` }}
                ></div>
                <div
                  className="thumb"
                  id="thumb"
                  style={{ left: `${budgetPct}%` }}
                ></div>
                <input
                  type="range"
                  id="brange"
                  min={BUDGET_MIN}
                  max={BUDGET_MAX}
                  step="500"
                  value={budget}
                  onChange={handleBudgetChange}
                />
              </div>
              <div className="scale">
                <span>$500</span>
                <span>$10K</span>
                <span>$25K</span>
                <span>$50K+</span>
              </div>
            </div>

            {error && <p className="error">{error}</p>}
            <div className="actions">
              <button className="back" onClick={() => go(2)} disabled={submitting}>
                ← Back
              </button>
              <button className="next" onClick={finish} disabled={submitting}>
                {submitting ? "Saving…" : "Finish Setup"}
                {!submitting && (
                  <span
                    style={{
                      fontFamily: "Instrument Serif, serif",
                      fontStyle: "italic",
                    }}
                  >
                    →
                  </span>
                )}
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
