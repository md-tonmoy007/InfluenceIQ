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

const severityClass = (severity: string | null | undefined) => {
  const normalized = (severity ?? "").toLowerCase();
  if (normalized === "high" || normalized === "critical") {
    return { avatar: "c-av-3", pill: "pill-neg" as const, glyph: "!" };
  }
  if (normalized === "medium") {
    return { avatar: "c-av-2", pill: "pill-neu" as const, glyph: "?" };
  }
  return { avatar: "c-av-1", pill: "pill-neu" as const, glyph: "!" };
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
          flags.map((flag) => {
            const tone = severityClass(flag.severity);
            return (
              <div className="comment" key={String(flag.flag_id ?? `${flag.risk_type}-${flag.reason}`)}>
                <div className={`cav ${tone.avatar}`} aria-hidden="true">
                  {tone.glyph}
                </div>
                <div className="body">
                  <div className="who">
                    {flag.risk_type ?? "Risk"} · {flag.severity ?? "review"}
                  </div>
                  <div className="txt">
                    {flag.reason ?? flag.context_snippet ?? "Flagged content requires review."}
                  </div>
                  {flag.source_url ? (
                    <div className="txt source-link">
                      <a href={flag.source_url} target="_blank" rel="noopener noreferrer">
                        {flag.source_url}
                      </a>
                    </div>
                  ) : null}
                </div>
                <span className={`pill ${tone.pill}`}>{flag.detection_method ?? "rule"}</span>
              </div>
            );
          })
        ) : (
          <div className="comment">
            <div className="cav c-av-2" aria-hidden="true">
              ✓
            </div>
            <div className="body">
              <div className="who">Clean profile</div>
              <div className="txt">
                No deterministic brand-safety flags were attached to this creator.
              </div>
            </div>
            <span className="pill pill-pos">Clear</span>
          </div>
        )}
      </div>
    </section>
  );
}
