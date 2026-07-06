"use client";

import type { CampaignWeights } from "@/types/campaign";

type WeightSlidersProps = {
  value: CampaignWeights;
  onChange: (next: CampaignWeights) => void;
};

const FIELDS: Array<{ key: keyof CampaignWeights; label: string }> = [
  { key: "relevance", label: "Relevance" },
  { key: "credibility", label: "Credibility" },
  { key: "engagement", label: "Engagement" },
  { key: "sentiment", label: "Sentiment" },
  { key: "brand_safety", label: "Brand safety" },
];

export function WeightSliders({ value, onChange }: WeightSlidersProps) {
  const total = FIELDS.reduce((sum, field) => sum + Number(value[field.key] ?? 0), 0);

  const handleChange = (changed: keyof CampaignWeights, newVal: number) => {
    const clamped = Math.max(0, Math.min(1, newVal));
    const oldVal = Number(value[changed] ?? 0);
    const delta = clamped - oldVal;

    const remaining = FIELDS.reduce((sum, f) => sum + (f.key === changed ? 0 : Number(value[f.key] ?? 0)), 0);
    if (remaining <= 0 && delta > 0) {
      return;
    }

    const next: CampaignWeights = { ...value, [changed]: clamped };
    for (const f of FIELDS) {
      if (f.key !== changed && remaining > 0) {
        const share = Number(value[f.key] ?? 0) / remaining;
        next[f.key] = Math.max(0, Number(value[f.key] ?? 0) - delta * share);
      }
    }
    onChange(next);
  };

  return (
    <div className="weight-sliders">
      {FIELDS.map((field) => (
        <label key={field.key} className="weight-sliders__row">
          <span>{field.label}</span>
          <input
            type="range"
            min={0}
            max={100}
            value={Math.round(Number(value[field.key] ?? 0) * 100)}
            onChange={(event) => {
              handleChange(field.key, Number(event.target.value) / 100);
            }}
          />
          <span>{Math.round(Number(value[field.key] ?? 0) * 100)}%</span>
        </label>
      ))}
      <p className="weight-sliders__total">Total weight: {Math.round(total * 100)}%</p>
    </div>
  );
}
