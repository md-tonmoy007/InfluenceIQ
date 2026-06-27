"use client";

type ScoreBreakdownPanelProps = {
  finalScore?: number | null;
  subScores?: Record<string, number | null | undefined>;
  positiveReasons?: string[];
  negativeReasons?: string[];
};

const scoreLabels: Record<string, string> = {
  relevance: "Relevance",
  credibility: "Credibility",
  engagement: "Engagement",
  sentiment: "Sentiment",
  brand_safety: "Brand safety",
};

const scoreDescriptions: Record<string, string> = {
  relevance: "How closely the creator's content aligns with your campaign goals and niche.",
  credibility: "Trust signals from verified sources, citations, and profile consistency.",
  engagement: "Audience interaction quality relative to follower count.",
  sentiment: "Tone and sentiment of the creator's public content and mentions.",
  brand_safety: "Risk flags, controversial topics, and brand-safe content indicators.",
};

const iconClasses = ["ri-1", "ri-2", "ri-3", "ri-4", "ri-5"] as const;

const formatScore = (value: number | null | undefined) =>
  value != null ? String(Math.round(value)) : "—";

export default function ScoreBreakdownPanel({
  finalScore,
  subScores = {},
  positiveReasons = [],
  negativeReasons = [],
}: ScoreBreakdownPanelProps) {
  const entries = Object.entries(scoreLabels).map(([key, label]) => ({
    key,
    label,
    value: subScores[key],
  }));

  return (
    <section className="panel">
      <div className="panel-head">
        <h3>
          <span className="pin"></span>Score breakdown
        </h3>
        <span className="meta">
          {finalScore != null ? `${Math.round(finalScore)}% campaign fit` : "No score yet"}
        </span>
      </div>

      <div className="reasons">
        {entries.map((entry, index) => (
          <div className="reason" key={entry.key}>
            <div
              className={`rico ${iconClasses[index] ?? iconClasses[0]}`}
              aria-hidden="true"
            >
              {formatScore(entry.value)}
            </div>
            <div className="body">
              <div className="t">{entry.label}</div>
              <div className="d">
                {scoreDescriptions[entry.key] ??
                  "Weighted signal from the campaign scoring pipeline."}
              </div>
              {entry.value != null ? (
                <div className="score-track" aria-hidden="true">
                  <div
                    className="score-fill"
                    style={{ width: `${Math.min(100, Math.max(0, entry.value))}%` }}
                  />
                </div>
              ) : null}
            </div>
          </div>
        ))}

        {positiveReasons.map((reason) => (
          <div className="reason" key={`pos-${reason}`}>
            <div className="rico ri-3" aria-hidden="true">
              +
            </div>
            <div className="body">
              <div className="t">Positive signal</div>
              <div className="d">{reason}</div>
            </div>
          </div>
        ))}

        {negativeReasons.map((reason) => (
          <div className="reason" key={`neg-${reason}`}>
            <div className="rico ri-4" aria-hidden="true">
              !
            </div>
            <div className="body">
              <div className="t">Risk signal</div>
              <div className="d">{reason}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
