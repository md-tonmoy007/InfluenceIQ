"use client";

type SafetyFlag = {
  flag_id?: string;
  risk_type?: string | null;
  reason?: string | null;
  severity?: string | null;
  detection_method?: string | null;
  matched_keyword?: string | null;
  context_snippet?: string | null;
  source_url?: string | null;
};

type SafetyFlagsPanelProps = {
  flags: SafetyFlag[];
};

export default function SafetyFlagsPanel({ flags }: SafetyFlagsPanelProps) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h3>
          <span className="pin"></span>Brand safety
        </h3>
        <span className="meta">
          {flags.length ? `${flags.length} flags` : "No flags recorded"}
        </span>
      </div>

      <div className="comments">
        {flags.length ? (
          flags.map((flag) => (
            <div className="comment" key={String(flag.flag_id ?? `${flag.risk_type}-${flag.reason}`)}>
              <div>
                <div className="who">
                  {flag.risk_type ?? "Risk"} · {flag.severity ?? "review"}
                </div>
                <div className="txt">
                  {flag.reason ?? flag.context_snippet ?? "Flagged content requires review."}
                </div>
                {flag.source_url ? (
                  <div className="txt" style={{ marginTop: "6px" }}>
                    Source: {flag.source_url}
                  </div>
                ) : null}
              </div>
              <span className="pill pill-neu">{flag.detection_method ?? "rule"}</span>
            </div>
          ))
        ) : (
          <div className="comment">
            <div>
              <div className="who">Clean profile</div>
              <div className="txt">
                No deterministic brand-safety flags were attached to this creator.
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
