"use client";

import { useEffect, useState } from "react";
import { getOnboarding, submitOnboarding } from "@/lib/api";
import {
  BUDGET_MAX,
  BUDGET_MIN,
  BUDGET_STEP,
  CAMPAIGN_GOAL_OPTIONS,
  CATEGORY_OPTIONS,
  COMPANY_SIZE_OPTIONS,
  COUNTRY_OPTIONS,
  DEFAULT_MONTHLY_BUDGET,
  PLATFORM_OPTIONS,
  budgetSliderPercent,
  normalizeCategory,
} from "@/lib/brandProfile";

export default function BrandForm() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(
    null
  );
  const [brandName, setBrandName] = useState("");
  const [industry, setIndustry] = useState<string>(CATEGORY_OPTIONS[1]);
  const [companySize, setCompanySize] = useState<string>(COMPANY_SIZE_OPTIONS[1]);
  const [country, setCountry] = useState<string>(COUNTRY_OPTIONS[1]);
  const [goals, setGoals] = useState<string[]>([]);
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [monthlyBudget, setMonthlyBudget] = useState(DEFAULT_MONTHLY_BUDGET);

  useEffect(() => {
    let cancelled = false;
    getOnboarding()
      .then((profile) => {
        if (cancelled) return;
        setBrandName(profile.brand_name);
        if (profile.industry) setIndustry(normalizeCategory(profile.industry));
        if (profile.company_size) setCompanySize(profile.company_size);
        if (profile.country) setCountry(profile.country);
        setGoals(profile.goals ?? []);
        setPlatforms(profile.platforms ?? []);
        setMonthlyBudget(profile.monthly_budget ?? DEFAULT_MONTHLY_BUDGET);
      })
      .catch(() => {
        if (cancelled) return;
        setBrandName("");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const toggleGoal = (goalId: string) => {
    setGoals((prev) =>
      prev.includes(goalId) ? prev.filter((id) => id !== goalId) : [...prev, goalId]
    );
  };

  const togglePlatform = (platformId: string) => {
    setPlatforms((prev) =>
      prev.includes(platformId)
        ? prev.filter((id) => id !== platformId)
        : [...prev, platformId]
    );
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      await submitOnboarding({
        brand_name: brandName.trim() || "Untitled brand",
        industry: normalizeCategory(industry),
        company_size: companySize,
        country,
        goals,
        platforms,
        monthly_budget: monthlyBudget,
      });
      setMessage({ type: "ok", text: "Brand profile saved." });
    } catch (err) {
      setMessage({
        type: "err",
        text: err instanceof Error ? err.message : "Failed to save brand profile",
      });
    } finally {
      setSaving(false);
    }
  };

  const budgetPct = budgetSliderPercent(monthlyBudget);

  if (loading) {
    return (
      <section className="card" id="brand">
        <h2>Brand</h2>
        <p className="desc">Loading…</p>
      </section>
    );
  }

  return (
    <section className="card" id="brand">
      <h2>Brand</h2>
      <p className="desc">
        Used to seed new briefs. Goals you select here are sent to match scoring when you
        create a campaign.
      </p>
      <form onSubmit={onSubmit}>
        <div className="row">
          <div className="field">
            <label>Brand name</label>
            <input
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              maxLength={255}
            />
          </div>
          <div className="field">
            <label>Industry</label>
            <select value={industry} onChange={(e) => setIndustry(e.target.value)}>
              {CATEGORY_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="row">
          <div className="field">
            <label>Country</label>
            <select value={country} onChange={(e) => setCountry(e.target.value)}>
              {COUNTRY_OPTIONS.map((opt) => (
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

        <div className="brand-section">
          <h3>Campaign goals</h3>
          <p className="brand-section-desc">
            Defaults for new briefs. All selected goals are included in campaign match
            scoring.
          </p>
          <div className="brand-chips">
            {CAMPAIGN_GOAL_OPTIONS.map((goal) => (
              <button
                key={goal.id}
                type="button"
                className={`brand-chip ${goals.includes(goal.id) ? "on" : ""}`}
                onClick={() => toggleGoal(goal.id)}
              >
                {goal.label}
              </button>
            ))}
          </div>
        </div>

        <div className="brand-section">
          <h3>Platforms</h3>
          <p className="brand-section-desc">
            The channels you focus on for influencer campaigns.
          </p>
          <div className="brand-platforms">
            {PLATFORM_OPTIONS.map((platform) => (
              <button
                key={platform.id}
                type="button"
                className={`brand-platform ${platforms.includes(platform.id) ? "on" : ""}`}
                onClick={() => togglePlatform(platform.id)}
              >
                <span className="brand-platform-name">{platform.label}</span>
                <span className="brand-platform-desc">{platform.desc}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="brand-section">
          <h3>Monthly budget</h3>
          <p className="brand-section-desc">
            Typical monthly spend on influencer campaigns.
          </p>
          <div className="brand-budget">
            <div className="brand-budget-head">
              <span className="brand-budget-value">
                ${monthlyBudget.toLocaleString()}
                <span className="brand-budget-unit">/mo</span>
              </span>
            </div>
            <div className="brand-slider">
              <div className="brand-slider-fill" style={{ width: `${budgetPct}%` }} />
              <div className="brand-slider-thumb" style={{ left: `${budgetPct}%` }} />
              <input
                type="range"
                min={BUDGET_MIN}
                max={BUDGET_MAX}
                step={BUDGET_STEP}
                value={monthlyBudget}
                onChange={(e) => setMonthlyBudget(parseInt(e.target.value, 10))}
                aria-label="Monthly budget"
              />
            </div>
            <div className="brand-slider-scale">
              <span>$500</span>
              <span>$10K</span>
              <span>$25K</span>
              <span>$50K+</span>
            </div>
          </div>
        </div>

        {message && (
          <p
            className="msg"
            style={{
              color: message.type === "ok" ? "var(--good)" : "var(--warn-ink)",
              fontSize: "12.5px",
              margin: "0 0 12px",
            }}
          >
            {message.text}
          </p>
        )}
        <button
          className="btn btn-primary btn-sm"
          type="submit"
          disabled={saving}
        >
          {saving ? "Saving…" : "Save brand profile"}
        </button>
      </form>
    </section>
  );
}
