"use client";

import { useEffect, useState } from "react";
import { getOnboarding, submitOnboarding, type BrandProfile } from "@/lib/api";

const INDUSTRY_OPTIONS = [
  "Outdoor & activewear",
  "Beauty & skincare",
  "Food & beverage",
  "Tech & SaaS",
  "Fashion & apparel",
  "Fitness & wellness",
  "Travel & hospitality",
  "Gaming & entertainment",
];

const COMPANY_SIZE_OPTIONS = ["1–10", "11–50", "51–200", "201–1000", "1000+"];

const COUNTRY_OPTIONS = [
  "United States",
  "Canada",
  "United Kingdom",
  "India",
  "Bangladesh",
  "Global",
];

export default function BrandForm() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(
    null
  );
  const [brandName, setBrandName] = useState("");
  const [industry, setIndustry] = useState(INDUSTRY_OPTIONS[0]);
  const [companySize, setCompanySize] = useState(COMPANY_SIZE_OPTIONS[1]);
  const [country, setCountry] = useState(COUNTRY_OPTIONS[1]);

  useEffect(() => {
    let cancelled = false;
    getOnboarding()
      .then((profile: BrandProfile) => {
        if (cancelled) return;
        setBrandName(profile.brand_name);
        if (profile.industry) setIndustry(profile.industry);
        if (profile.company_size) setCompanySize(profile.company_size);
        if (profile.country) setCountry(profile.country);
      })
      .catch(() => {
        // 404 means the user hasn't onboarded yet — fall back to
        // blank defaults so they can fill the form from scratch.
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

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      await submitOnboarding({
        brand_name: brandName.trim() || "Untitled brand",
        industry,
        company_size: companySize,
        country,
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
      <p className="desc">Used to seed match scoring across all your briefs.</p>
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
            <select
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
            >
              {INDUSTRY_OPTIONS.map((opt) => (
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
