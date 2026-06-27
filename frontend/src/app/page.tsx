import "./landing.css";
import Link from "next/link";
import LandingInteractions from "@/components/landing/LandingInteractions";
import LandingNav from "@/components/landing/LandingNav";
import LandingPriceCta from "@/components/landing/LandingPriceCta";

export const metadata = {
  title: "InfluenceIQ \u2014 Find the Perfect Influencer. Instantly.",
  description:
    "Describe your brand in a sentence. InfluenceIQ scans 2.4M vetted creators, ranks them on audience fit, brand safety, and historical ROAS \u2014 and hands you a campaign-ready shortlist in seconds.",
};

const StarSVG = () => (
  <svg viewBox="0 0 24 24">
    <path d="M12 2l3 6.5 7 .9-5.3 4.7 1.6 6.9L12 17.5 5.7 21l1.6-6.9L2 9.4l7-.9L12 2z" />
  </svg>
);

const FiveStars = () => (
  <div className="rating" aria-label="5 stars">
    <StarSVG />
    <StarSVG />
    <StarSVG />
    <StarSVG />
    <StarSVG />
  </div>
);

export default function LandingPage() {
  return (
    <>
      {/* ===== LANDING ===== */}
      <div className="landing">

        <LandingNav />

        {/* ── Hero ── */}
        <section className="hero">
          <div className="aurora" aria-hidden="true">
            <div className="blob b1"></div>
            <div className="blob b2"></div>
            <div className="blob b3"></div>
          </div>
          <div className="hero-grid">
            <div>
              <span className="hero-eyebrow">
                <span className="badge">New</span>
                AI matching v3 &mdash; 14&times; faster across 2.4M creators
              </span>
              <h1>
                Find the perfect<br />
                influencer.<br />
                <span className="accent">Instantly.</span>
              </h1>
              <p className="lede">
                Describe your brand in a sentence. InfluenceIQ scans 2.4M vetted creators,
                ranks them on audience fit, brand safety, and historical ROAS &mdash; and hands
                you a campaign-ready shortlist in seconds.
              </p>
              <div className="hero-actions">
                <Link className="btn btn-primary btn-lg" href="/signup" id="cta-find">
                  Find Influencers
                  <span className="arrow" aria-hidden="true">&rarr;</span>
                </Link>
                <button className="btn btn-ghost btn-lg" type="button">
                  <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                    <polygon points="6,4 20,12 6,20" />
                  </svg>
                  Watch 90-second demo
                </button>
              </div>
              <div className="hero-meta">
                <span><span className="dot"></span>Free to start &mdash; no card required</span>
                <span>SOC 2 Type II</span>
                <span>GDPR &amp; CCPA</span>
              </div>
            </div>

            {/* Visual: AI prompt + live match results */}
            <div className="search-card" aria-hidden="true">
              <div className="label"><span className="lpin"></span>Brand brief &middot; processing</div>
              <div className="prompt"><span id="typed"></span><span className="caret"></span></div>
              <div className="runline"></div>
              <div className="match-list">
                <div className="match">
                  <div className="avatar a1">MG</div>
                  <div>
                    <div className="name">Maya Greene</div>
                    <div className="meta">@mayagreene &middot; 412K &middot; Wellness &middot; Toronto</div>
                  </div>
                  <span className="score good">96 match</span>
                </div>
                <div className="match">
                  <div className="avatar a2">SR</div>
                  <div>
                    <div className="name">Sofia Reyes</div>
                    <div className="meta">@sofreyes &middot; 287K &middot; Pilates &middot; Austin</div>
                  </div>
                  <span className="score good">94 match</span>
                </div>
                <div className="match">
                  <div className="avatar a3">JC</div>
                  <div>
                    <div className="name">Jordan Chen</div>
                    <div className="meta">@runwithjordan &middot; 198K &middot; Running &middot; Brooklyn</div>
                  </div>
                  <span className="score">91 match</span>
                </div>
                <div className="match">
                  <div className="avatar a4">AT</div>
                  <div>
                    <div className="name">Ava Thompson</div>
                    <div className="meta">@avamoves &middot; 156K &middot; Strength &middot; Denver</div>
                  </div>
                  <span className="score">88 match</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── Logos marquee ── */}
        <div className="logos">
          <div className="logos-inner">
            <span className="lbl">Trusted by 1,200+ brands</span>
            <div className="marquee">
              <div className="marquee-track" id="marquee-track">
                {/* duplicated by LandingInteractions for seamless loop */}
              </div>
            </div>
          </div>
        </div>

        {/* ===== Section 1 — Problem Statement ===== */}
        <section className="problem">
          <div className="bg-aurora" aria-hidden="true">
            <span className="b b1"></span>
            <span className="b b2"></span>
            <span className="b b3"></span>
          </div>
          <div className="problem-inner">
            <div className="eyebrow-row">The reality</div>
            <h2 className="sec-h2">
              Influencer marketing is broken in the <span className="accent">middle.</span>
            </h2>
            <p className="sec-lede">
              Brand managers know what they want. Creators know who they reach. The gap between them eats your week &mdash; and your budget.
            </p>

            <div className="stat-strip">
              <div><div className="n">47h</div><div className="l">avg time per shortlist</div></div>
              <div><div className="n">68%</div><div className="l">of picks under-perform</div></div>
              <div><div className="n">$12K</div><div className="l">avg wasted on bad fits</div></div>
              <div><div className="n">3.4&times;</div><div className="l">cost vs the right creator</div></div>
            </div>

            <div className="problem-grid">
              <article className="pain-card">
                <span className="strike">Today</span>
                <h3>Hours wasted scrolling feeds for the right creator</h3>
                <p className="quant"><b>47</b> hours per campaign on average &mdash; open 30 tabs, bookmark 6 profiles, forget by Friday.</p>
                <div className="vis">
                  <div className="pain-tabs">
                    <div className="pain-tab"><span className="ico"></span>@maya_wellness &middot; IG<span className="x">&times;</span></div>
                    <div className="pain-tab"><span className="ico"></span>@runwithjordan &middot; YT<span className="x">&times;</span></div>
                    <div className="pain-tab"><span className="ico"></span>@thatpilatesgirl_2 &middot; IG<span className="x">&times;</span></div>
                    <div className="pain-tab dim"><span className="ico"></span>+ 27 more open tabs<span className="x">&times;</span></div>
                  </div>
                </div>
              </article>

              <article className="pain-card">
                <span className="strike">Today</span>
                <h3>Influencers whose audience doesn&apos;t actually match yours</h3>
                <p className="quant"><b>68%</b> of picked creators reach the wrong age or geography &mdash; big numbers, wrong people.</p>
                <div className="vis">
                  <div className="pain-donut">
                    <svg width="84" height="84" viewBox="0 0 84 84">
                      <circle cx="42" cy="42" r="32" fill="none" stroke="var(--paper-2)" strokeWidth="11" />
                      <circle cx="42" cy="42" r="32" fill="none" stroke="oklch(0.65 0.20 25)" strokeWidth="11" strokeDasharray="62 201" transform="rotate(-90 42 42)" />
                      <circle cx="42" cy="42" r="32" fill="none" stroke="var(--good)" strokeWidth="11" strokeDasharray="40 201" strokeDashoffset="-62" transform="rotate(-90 42 42)" />
                    </svg>
                    <div className="legend">
                      <div className="row"><span className="sw" style={{ background: "var(--good)" }}></span>Right fit <b style={{ marginLeft: "auto", color: "var(--ink)" }}>20%</b></div>
                      <div className="row miss"><span className="sw" style={{ background: "oklch(0.65 0.20 25)" }}></span>Wrong age <b style={{ marginLeft: "auto" }}>31%</b></div>
                      <div className="row miss"><span className="sw" style={{ background: "var(--paper-2)", border: "1px solid var(--line)" }}></span>Wrong geo <b style={{ marginLeft: "auto" }}>49%</b></div>
                    </div>
                  </div>
                </div>
              </article>

              <article className="pain-card">
                <span className="strike">Today</span>
                <h3>No clarity on what your campaign budget actually buys</h3>
                <p className="quant"><b>$12K</b> spent before you see a single performance signal &mdash; explain that to your CMO.</p>
                <div className="vis">
                  <div className="pain-invoice">
                    <div className="row"><span>1&times; IG Reel</span><span>$2,400</span></div>
                    <div className="row"><span>Est. reach</span><span className="q">??</span></div>
                    <div className="row"><span>Est. engagement</span><span className="q">??</span></div>
                    <div className="row"><span>Cost / engagement</span><span className="q">??</span></div>
                    <div className="row"><span>Total commitment</span><span>$12,000</span></div>
                  </div>
                </div>
              </article>
            </div>
          </div>
        </section>

        {/* ===== Section 2 — Product Showcase ===== */}
        <section className="showcase">
          <div className="showcase-inner">
            <div className="showcase-head">
              <div className="eyebrow-row">The product</div>
              <h2 className="sec-h2">AI that does the <span className="accent">research</span> for you.</h2>
              <p className="sec-lede">Describe your campaign. Our AI analyzes 50,000+ profiles and returns your top matches in seconds.</p>
            </div>

            <div className="showcase-stage">
              <div className="showcase-window">
                <div className="browser-bar">
                  <div className="dots"><span></span><span></span><span></span></div>
                  <div className="url"><span className="lock">&#9679;</span><strong>app.influenceiq.com</strong>/discover</div>
                </div>
                <div className="showcase-grid">
                  {/* Left: brief + progress */}
                  <div className="showcase-left">
                    <h4>Campaign brief</h4>
                    <div className="desc">Live &middot; drafted in seconds</div>
                    <div className="showcase-prompt">
                      <div className="lbl">Brand input</div>
                      <span id="sc-typed"></span><span className="caret"></span>
                    </div>

                    <div className="showcase-progress">
                      <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: "9.5px", letterSpacing: "0.08em", color: "var(--muted)", textTransform: "uppercase", marginBottom: "8px" }}>Matching &middot; v3</div>
                      <div className="sp-row" data-i="0"><span className="dot"></span><span>Parsing brief</span><span className="ms">0.4s</span></div>
                      <div className="sp-row" data-i="1"><span className="dot"></span><span>Scanning 50,247 profiles</span><span className="ms">1.2s</span></div>
                      <div className="sp-row" data-i="2"><span className="dot"></span><span>Scoring fit &amp; safety</span><span className="ms">0.8s</span></div>
                      <div className="sp-row" data-i="3"><span className="dot"></span><span>Ranking top matches</span><span className="ms">0.6s</span></div>
                    </div>
                  </div>

                  {/* Right: ranked matches */}
                  <div className="showcase-right">
                    <div className="showcase-beam" aria-hidden="true"></div>
                    <h4>Top matches <span className="badge">LIVE</span></h4>
                    <div className="desc">Ranked from 50,247 indexed creators</div>
                    <div className="showcase-cards">
                      <div className="sw-card">
                        <span className="sw-rank">1</span>
                        <span className="av" style={{ background: "linear-gradient(135deg,#6a4cff,#c054ff)" }}>MG</span>
                        <div>
                          <div className="nm">Maya Greene</div>
                          <div className="mt">@mayagreene &middot; 412K &middot; Wellness</div>
                        </div>
                        <span className="sc h">96</span>
                      </div>
                      <div className="sw-card">
                        <span className="sw-rank">2</span>
                        <span className="av" style={{ background: "linear-gradient(135deg,#ff7a59,#ff4d8a)" }}>SR</span>
                        <div>
                          <div className="nm">Sofia Reyes</div>
                          <div className="mt">@sofreyes &middot; 287K &middot; Pilates</div>
                        </div>
                        <span className="sc h">94</span>
                      </div>
                      <div className="sw-card">
                        <span className="sw-rank">3</span>
                        <span className="av" style={{ background: "linear-gradient(135deg,#14b8d4,#2563eb)" }}>JC</span>
                        <div>
                          <div className="nm">Jordan Chen</div>
                          <div className="mt">@runwithjordan &middot; 198K &middot; Running</div>
                        </div>
                        <span className="sc m">91</span>
                      </div>
                      <div className="sw-card">
                        <span className="sw-rank">4</span>
                        <span className="av" style={{ background: "linear-gradient(135deg,#2bb673,#5ad6a0)" }}>AT</span>
                        <div>
                          <div className="nm">Ava Thompson</div>
                          <div className="mt">@avamoves &middot; 156K &middot; Strength</div>
                        </div>
                        <span className="sc m">88</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <p className="showcase-caption">From campaign brief to matched influencer list &mdash; <strong>under 5 seconds.</strong></p>
            </div>
          </div>
        </section>

        {/* ===== Section 3 — How It Works (vertical timeline) ===== */}
        <section className="how-section" id="how">
          <div className="bg-aurora" aria-hidden="true">
            <span className="b b1" style={{ opacity: 0.18 }}></span>
            <span className="b b3" style={{ opacity: 0.18 }}></span>
          </div>
          <div className="section-head">
            <div className="eyebrow-row">How it works</div>
            <h2 className="sec-h2">Three steps. <span className="accent">No agency.</span></h2>
            <p className="sec-lede">A focused workflow built for performance marketing teams who&apos;d rather launch than scroll.</p>
          </div>

          <div className="how-timeline">
            <article className="how-step">
              <div className="how-num">1</div>
              <div className="how-body">
                <h3>Describe Your Campaign <span className="step-kw">~ 2 min</span></h3>
                <p>Tell us your product, audience, budget and goals. The more you give us, the sharper the match.</p>
              </div>
              <div className="how-vis">
                <div className="label">Brand brief</div>
                <div className="how-vis-chips">
                  <span className="c solid">Sustainable</span>
                  <span className="c">Activewear</span>
                  <span className="c">Women 25&ndash;34</span>
                  <span className="c">North America</span>
                  <span className="c">Pilates</span>
                </div>
              </div>
            </article>

            <article className="how-step">
              <div className="how-num">2</div>
              <div className="how-body">
                <h3>AI Finds Your Matches <span className="step-kw">~ 5 sec</span></h3>
                <p>We scan 50,000+ influencer profiles across all major platforms and score them against your brief.</p>
              </div>
              <div className="how-vis">
                <div className="label">Match scoring</div>
                <div className="how-vis-bars">
                  <div className="r"><span className="nm">Audience fit</span><span className="br"><span style={{ width: "96%", background: "linear-gradient(90deg,var(--violet),var(--cyan))" }}></span></span><span className="pc">96</span></div>
                  <div className="r"><span className="nm">Brand safety</span><span className="br"><span style={{ width: "88%", background: "linear-gradient(90deg,var(--coral),var(--violet))" }}></span></span><span className="pc">88</span></div>
                  <div className="r"><span className="nm">Past ROAS</span><span className="br"><span style={{ width: "74%", background: "linear-gradient(90deg,var(--cyan),var(--good))" }}></span></span><span className="pc">74</span></div>
                </div>
              </div>
            </article>

            <article className="how-step">
              <div className="how-num">3</div>
              <div className="how-body">
                <h3>Contact &amp; Launch <span className="step-kw">~ 1 day</span></h3>
                <p>Access contact details, save shortlists, and reach out directly from InfluenceIQ &mdash; no spreadsheet handoffs.</p>
              </div>
              <div className="how-vis">
                <div className="label">Campaigns</div>
                <div className="how-vis-launch"><span className="pill">LIVE</span><span className="txt">SS26 Pilates capsule &middot; 12 creators</span><span className="amt">$48.2K</span></div>
                <div className="how-vis-launch"><span className="pill draft">DRAFT</span><span className="txt">Holiday gifting &middot; 24 creators</span><span className="amt">&mdash;</span></div>
              </div>
            </article>
          </div>
        </section>

        {/* ===== Section 4 — Features (Bento grid) ===== */}
        <section className="features">
          <div className="features-inner">
            <div className="features-head">
              <div className="eyebrow-row">What&apos;s inside</div>
              <h2 className="sec-h2">Everything you need to <span className="accent">go live.</span></h2>
              <p className="sec-lede">Six capabilities working together &mdash; so you can stop juggling spreadsheets and start running campaigns.</p>
            </div>

            <div className="bento">
              {/* Feat 1 — large featured */}
              <article className="feat feat-1">
                <div className="feat-head">
                  <span className="ico">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                      <path d="M12 3l1.8 4.5L18 9.3l-4.2 1.8L12 15.6l-1.8-4.5L6 9.3l4.2-1.8L12 3z" />
                    </svg>
                  </span>
                  <span className="pin">Flagship</span>
                </div>
                <h3 style={{ fontSize: "22px" }}>AI Match Scoring</h3>
                <p>Every influencer gets a match score tailored to your brief &mdash; audience fit, brand safety, ROAS history, and content quality, rolled into one number you can defend in a meeting.</p>
                <div className="demo">
                  <div className="demo-row">
                    <span className="demo-av" style={{ background: "linear-gradient(135deg,#6a4cff,#c054ff)" }}>MG</span>
                    <div><div className="demo-nm">Maya Greene</div><div className="demo-mt">412K &middot; Wellness</div></div>
                    <span className="demo-bar"><i style={{ width: "96%" }}></i></span><span className="demo-sc">96</span>
                  </div>
                  <div className="demo-row">
                    <span className="demo-av" style={{ background: "linear-gradient(135deg,#ff7a59,#ff4d8a)" }}>SR</span>
                    <div><div className="demo-nm">Sofia Reyes</div><div className="demo-mt">287K &middot; Pilates</div></div>
                    <span className="demo-bar"><i style={{ width: "94%", animationDelay: ".15s" }}></i></span><span className="demo-sc">94</span>
                  </div>
                  <div className="demo-row">
                    <span className="demo-av" style={{ background: "linear-gradient(135deg,#14b8d4,#2563eb)" }}>JC</span>
                    <div><div className="demo-nm">Jordan Chen</div><div className="demo-mt">198K &middot; Running</div></div>
                    <span className="demo-bar"><i style={{ width: "91%", animationDelay: ".3s" }}></i></span><span className="demo-sc">91</span>
                  </div>
                  <div className="demo-row">
                    <span className="demo-av" style={{ background: "linear-gradient(135deg,#2bb673,#5ad6a0)" }}>AT</span>
                    <div><div className="demo-nm">Ava Thompson</div><div className="demo-mt">156K &middot; Strength</div></div>
                    <span className="demo-bar"><i style={{ width: "88%", animationDelay: ".45s" }}></i></span><span className="demo-sc">88</span>
                  </div>
                </div>
              </article>

              {/* Feat 2 */}
              <article className="feat feat-2">
                <div className="feat-head">
                  <span className="ico">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                      <circle cx="12" cy="8" r="4" /><path d="M3 21a9 9 0 0 1 18 0" />
                    </svg>
                  </span>
                </div>
                <h3>Audience Demographics</h3>
                <p>Age, gender and location breakdown of any creator&apos;s audience.</p>
                <div className="demo">
                  <svg viewBox="0 0 120 120">
                    <circle cx="60" cy="60" r="42" fill="none" stroke="var(--paper-2)" strokeWidth="12" />
                    <circle cx="60" cy="60" r="42" fill="none" stroke="oklch(0.74 0.18 30)" strokeWidth="12" strokeDasharray="206 264" transform="rotate(-90 60 60)" />
                    <circle cx="60" cy="60" r="42" fill="none" stroke="oklch(0.58 0.22 285)" strokeWidth="12" strokeDasharray="50 264" strokeDashoffset="-206" transform="rotate(-90 60 60)" />
                    <text x="60" y="64" textAnchor="middle" fontSize="13" fontWeight="500" fontFamily="Geist" fill="var(--ink)">F 78%</text>
                  </svg>
                </div>
              </article>

              {/* Feat 3 */}
              <article className="feat feat-3">
                <div className="feat-head">
                  <span className="ico">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                      <circle cx="12" cy="12" r="9" /><path d="M8 14c1 1.5 2.5 2 4 2s3-.5 4-2" />
                      <circle cx="9" cy="10" r="0.6" fill="currentColor" /><circle cx="15" cy="10" r="0.6" fill="currentColor" />
                    </svg>
                  </span>
                </div>
                <h3>Sentiment Analysis</h3>
                <p>We read comment tone so you know how audiences really feel.</p>
                <div className="demo">
                  <div className="sent-bar"><span className="p"></span><span className="n"></span><span className="g"></span></div>
                  <div className="leg"><span><b>84%</b> pos</span><span><b>13%</b> neu</span><span><b>3%</b> neg</span></div>
                </div>
              </article>

              {/* Feat 4 */}
              <article className="feat feat-4">
                <div className="feat-head">
                  <span className="ico">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                      <path d="M12 1v22M5 8h11a3 3 0 0 1 0 6H8a3 3 0 0 0 0 6h12" />
                    </svg>
                  </span>
                </div>
                <h3>Budget Intelligence</h3>
                <p>Estimated rates and ROI projections before you commit.</p>
                <div className="demo">
                  <span className="bar" style={{ height: "42%" }}></span>
                  <span className="bar" style={{ height: "62%" }}></span>
                  <span className="bar" style={{ height: "38%" }}></span>
                  <span className="bar" style={{ height: "78%" }}></span>
                  <span className="bar" style={{ height: "54%" }}></span>
                  <span className="bar" style={{ height: "88%" }}></span>
                  <span className="bar" style={{ height: "70%" }}></span>
                </div>
              </article>

              {/* Feat 5 */}
              <article className="feat feat-5">
                <div className="feat-head">
                  <span className="ico">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                      <rect x="3" y="3" width="7" height="7" rx="1.4" /><rect x="14" y="3" width="7" height="7" rx="1.4" />
                      <rect x="3" y="14" width="7" height="7" rx="1.4" /><rect x="14" y="14" width="7" height="7" rx="1.4" />
                    </svg>
                  </span>
                </div>
                <h3>Multi-Platform Coverage</h3>
                <p>YouTube, Instagram, Facebook, TikTok &mdash; all in one place.</p>
                <div className="demo">
                  <span className="plat ig">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                      <rect x="3" y="3" width="18" height="18" rx="5" /><circle cx="12" cy="12" r="4" />
                      <circle cx="17.5" cy="6.5" r="0.6" fill="white" />
                    </svg>
                  </span>
                  <span className="plat yt">
                    <svg width="18" height="14" viewBox="0 0 24 18" fill="white">
                      <path d="M23.5 3.5a3 3 0 0 0-2.1-2.1C19.5 1 12 1 12 1s-7.5 0-9.4.4A3 3 0 0 0 .5 3.5C.1 5.4.1 9 .1 9s0 3.6.4 5.5a3 3 0 0 0 2.1 2.1C4.5 17 12 17 12 17s7.5 0 9.4-.4a3 3 0 0 0 2.1-2.1c.4-1.9.4-5.5.4-5.5s0-3.6-.4-5.5zM9.5 12.5v-7L15.5 9l-6 3.5z" />
                    </svg>
                  </span>
                  <span className="plat tt">
                    <svg width="14" height="17" viewBox="0 0 20 22" fill="white">
                      <path d="M14.5 1c.4 1.8 1.5 3.4 3 4.4 1.1.7 2.5 1.1 3.9 1.1V11c-1.6 0-3.2-.4-4.6-1.1-.6-.3-1.2-.7-1.7-1.1v6.6c0 4.1-3.4 7.5-7.5 7.5-1.6 0-3.1-.5-4.3-1.4-1.9-1.4-3.2-3.7-3.2-6.2 0-4.1 3.4-7.5 7.5-7.5.4 0 .9 0 1.3.1v4.4c-.4-.1-.8-.2-1.3-.2-1.7 0-3.1 1.4-3.1 3.1s1.4 3.2 3.2 3.2 3.2-1.4 3.2-3.1V1h3.6z" />
                    </svg>
                  </span>
                  <span className="plat fb">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
                      <path d="M14 9V7c0-1 .5-2 2-2h2V1h-3c-3 0-5 2-5 5v3H7v4h3v9h4v-9h3l1-4h-4z" />
                    </svg>
                  </span>
                </div>
              </article>

              {/* Feat 6 */}
              <article className="feat feat-6">
                <div className="feat-head">
                  <span className="ico">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                      <path d="M19 21l-7-4.5L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16Z" />
                    </svg>
                  </span>
                </div>
                <h3>Saved Campaign Lists</h3>
                <p>Shortlist favorites and organize by campaign.</p>
                <div className="demo">
                  <div className="list-row"><span className="sw"></span><span className="nm">Ramadan Campaign 2026</span><span className="ct">14</span></div>
                  <div className="list-row"><span className="sw" style={{ background: "linear-gradient(135deg,var(--cyan),var(--violet))" }}></span><span className="nm">SS26 Trail capsule</span><span className="ct">9</span></div>
                  <div className="list-row"><span className="sw" style={{ background: "linear-gradient(135deg,var(--coral),var(--cyan))" }}></span><span className="nm">Gen Z fintech &mdash; Q3</span><span className="ct">21</span></div>
                </div>
              </article>
            </div>
          </div>
        </section>

        {/* ===== Section 5 — Testimonials ===== */}
        <section className="testimonials">
          <div className="testimonials-inner">
            <div className="test-head">
              <div className="eyebrow-row">Brands that switched</div>
              <h2 className="sec-h2">From <span className="accent">&ldquo;who do we pick?&rdquo;</span> to &ldquo;they&apos;re already live.&rdquo;</h2>
            </div>

            <div className="test-layout">
              {/* Featured */}
              <article className="test-feature">
                <span className="mark">&ldquo;</span>
                <FiveStars />
                <p className="quote">InfluenceIQ cut our influencer research time by <em>80%</em>. We found creators we never would have discovered manually, and every match felt genuinely relevant to our audience.</p>
                <div className="author">
                  <span className="av" style={{ background: "linear-gradient(135deg,#ec4899,#a855f7)" }}>NR</span>
                  <div className="meta">
                    <div className="nm">Nadia Rahman</div>
                    <div className="tt">Marketing Manager &middot; <b>StyleDhaka</b></div>
                  </div>
                </div>
              </article>

              {/* Side mini */}
              <div className="test-side">
                <article className="test-mini test-mini-1">
                  <FiveStars />
                  <p className="quote">Finding micro-influencers in a niche market used to take weeks. Now we get a shortlist in seconds with engagement data we can actually trust.</p>
                  <div className="author">
                    <span className="av" style={{ background: "linear-gradient(135deg,#10b981,#14b8d4)" }}>JO</span>
                    <div className="meta"><div className="nm">James Okonkwo</div><div className="tt">Growth Lead &middot; Lagos Eats</div></div>
                  </div>
                </article>
                <article className="test-mini test-mini-2">
                  <FiveStars />
                  <p className="quote">The AI match score is surprisingly accurate. Our last campaign hit 4.8% engagement &mdash; nearly double what we were getting before.</p>
                  <div className="author">
                    <span className="av" style={{ background: "linear-gradient(135deg,#f59e0b,#ef4444)" }}>PM</span>
                    <div className="meta"><div className="nm">Priya Mehta</div><div className="tt">Brand Director &middot; GlowCo India</div></div>
                  </div>
                </article>
              </div>
            </div>
          </div>
        </section>

        {/* ===== Section 6 — Pricing ===== */}
        <section className="pricing" id="pricing">
          <div className="pricing-inner">
            <div className="pricing-head">
              <div className="eyebrow-row">Pricing</div>
              <h2 className="sec-h2">Simple plans. <span className="accent">No hidden seats.</span></h2>
              <p className="sec-lede">Start free, upgrade when you&apos;re sending briefs. Cancel anytime.</p>

              <div className="billing-toggle" id="billing">
                <button type="button" className="on" data-b="monthly">Monthly</button>
                <button type="button" data-b="annual">Annual <span className="save">SAVE 20%</span></button>
              </div>
            </div>

            <div className="price-grid">
              <article className="price-card">
                <h3 className="price-tier">Explorer</h3>
                <div className="price-value" data-price="0" data-yearly="0"><span className="amt">$0</span></div>
                <p className="price-tagline">For curious marketers kicking the tires.</p>
                <div className="price-divider"></div>
                <ul className="price-features">
                  <li><b>10</b>&nbsp;searches per month</li>
                  <li>Basic creator profiles</li>
                  <li><b>1</b>&nbsp;saved list</li>
                  <li>No contact reveal</li>
                </ul>
                <LandingPriceCta plan="explorer" guestHref="/signup" guestLabel="Get Started Free" />
              </article>

              <article className="price-card popular">
                <h3 className="price-tier">Growth</h3>
                <div className="price-value" data-price="29" data-yearly="23"><span className="currency">$</span><span className="amt">29</span><span className="per">/ month</span></div>
                <p className="price-tagline">For marketing teams running real campaigns.</p>
                <div className="price-divider"></div>
                <ul className="price-features">
                  <li><b>Unlimited</b>&nbsp;searches</li>
                  <li>Full analytics &amp; demographics</li>
                  <li>Contact reveal</li>
                  <li>Unlimited saved lists</li>
                  <li>Campaign brief builder</li>
                  <li>ROI estimator</li>
                </ul>
                <LandingPriceCta
                  plan="growth"
                  guestHref="/signup"
                  guestLabel="Start Free Trial"
                  filled
                />
              </article>

              <article className="price-card">
                <h3 className="price-tier">Scale</h3>
                <div className="price-value"><span className="custom">Custom</span></div>
                <p className="price-tagline">For agencies and in-house teams at scale.</p>
                <div className="price-divider"></div>
                <ul className="price-features">
                  <li>Everything in Growth</li>
                  <li>API access</li>
                  <li>Team seats &amp; SSO</li>
                  <li>Dedicated support</li>
                </ul>
                <LandingPriceCta plan="scale" guestHref="#" guestLabel="Contact Sales" />
              </article>
            </div>

            <p className="price-foot">14-day free trial &middot; <strong>no credit card required</strong> &middot; cancel anytime</p>
          </div>
        </section>

        {/* ===== Section 7 — Final CTA ===== */}
        <section className="final-cta">
          <div className="final-cta-inner">
            <div className="final-cta-mini m1" aria-hidden="true">
              <span className="av" style={{ background: "linear-gradient(135deg,#6a4cff,#c054ff)" }}>MG</span>
              <span>@mayagreene</span>
              <span className="sc">96</span>
            </div>
            <div className="final-cta-mini m2" aria-hidden="true">
              <span className="av" style={{ background: "linear-gradient(135deg,#ff7a59,#ff4d8a)" }}>SR</span>
              <span>@sofreyes</span>
              <span className="sc">94</span>
            </div>
            <div className="final-cta-mini m3" aria-hidden="true">
              <span className="av" style={{ background: "linear-gradient(135deg,#14b8d4,#2563eb)" }}>JC</span>
              <span>@runwithjordan</span>
              <span className="sc">91</span>
            </div>
            <div className="final-cta-mini m4" aria-hidden="true">
              <span className="av" style={{ background: "linear-gradient(135deg,#2bb673,#5ad6a0)" }}>AT</span>
              <span>@avamoves</span>
              <span className="sc">88</span>
            </div>

            <h2>Your next campaign deserves the <span className="accent">right voice.</span></h2>
            <p className="subh">Join 500+ brands already using InfluenceIQ to find creators that convert.</p>
            <div className="cta-actions">
              <Link className="btn-final" href="/signup">
                Get Started Free
                <span className="arrow" aria-hidden="true">&rarr;</span>
              </Link>
              <span className="small">No credit card required</span>
            </div>
          </div>
        </section>

        <footer className="footer">
          <div className="footer-inner">
            <span>&copy; 2026 InfluenceIQ, Inc.</span>
            <div className="footer-links">
              <a href="#">Privacy</a>
              <a href="#">Terms</a>
              <a href="#">Security</a>
              <a href="#">Contact</a>
            </div>
          </div>
        </footer>

      </div>

      <LandingInteractions />
    </>
  );
}
