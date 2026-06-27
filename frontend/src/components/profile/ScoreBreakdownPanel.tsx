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
        {entries.map((entry) => (
          <div className="reason" key={entry.key}>
            <div className="body">
              <div className="t">
                {entry.label}
                {entry.value != null ? `: ${Math.round(entry.value)}` : ": —"}
              </div>
              <div className="d">
                Weighted signal from the campaign scoring pipeline.
              </div>
            </div>
          </div>
        ))}

        {positiveReasons.map((reason) => (
          <div className="reason" key={`pos-${reason}`}>
            <div className="body">
              <div className="t">Positive signal</div>
              <div className="d">{reason}</div>
            </div>
          </div>
        ))}

        {negativeReasons.map((reason) => (
          <div className="reason" key={`neg-${reason}`}>
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
