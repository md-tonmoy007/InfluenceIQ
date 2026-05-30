"use client";

import React, { useState } from "react";

type RangeFilterProps = {
  label: string;
  min: number;
  max: number;
  step: number;
  initialValue: number;
  id: string;
  unit?: string;
  prefix?: string;
  format?: "currency" | "percent" | "number";
};

export default function RangeFilter({
  label,
  min,
  max,
  step,
  initialValue,
  id,
  unit = "",
  prefix = "",
  format,
}: RangeFilterProps) {
  const [value, setValue] = useState(initialValue);

  const pct = ((value - min) / (max - min)) * 100;

  let displayValue = `${prefix}${value}${unit}`;
  if (format === "currency") {
    displayValue = `$500 – $${value.toLocaleString()}`;
  } else if (format === "percent") {
    displayValue = `${value}%`;
  } else if (format === "number") {
    displayValue = `${value}`;
  }

  return (
    <div className="filter-section">
      <div className="label">
        {label} <span className="v mono">{displayValue}</span>
      </div>
      <div className="slider-row">
        <span className="min">
          {prefix}
          {min}
          {unit}
        </span>
        <span>{unit || "Value"}</span>
        <span className="max">
          {prefix}
          {max.toLocaleString()}
          {unit}
        </span>
      </div>
      <input
        type="range"
        className="range"
        min={min}
        max={max}
        step={step}
        value={value}
        id={id}
        style={{ "--p": `${pct}%` } as React.CSSProperties}
        onChange={(e) => setValue(parseFloat(e.target.value))}
      />
    </div>
  );
}
