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
              const nextValue = Number(event.target.value) / 100;
              onChange({ ...value, [field.key]: nextValue });
            }}
          />
          <span>{Math.round(Number(value[field.key] ?? 0) * 100)}%</span>
        </label>
      ))}
      <p className="weight-sliders__total">Total weight: {Math.round(total * 100)}%</p>
    </div>
  );
}
