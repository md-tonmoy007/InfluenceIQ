"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function OnboardingStepper() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [goals, setGoals] = useState<string[]>(["awareness", "sales"]);
  const [platforms, setPlatforms] = useState<string[]>(["instagram", "tiktok"]);
  const [budget, setBudget] = useState(12500);

  const go = (s: number) => {
    setStep(s);
    window.scrollTo({ top: 0 });
  };

  const toggleGoal = (g: string) => {
    setGoals((prev) =>
      prev.includes(g) ? prev.filter((x) => x !== g) : [...prev, g]
    );
  };

  const togglePlatform = (p: string) => {
    setPlatforms((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  };

  const handleBudgetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setBudget(parseInt(e.target.value, 10));
  };

  const finish = () => {
    router.push("/dashboard?welcome=1");
  };

  const budgetPct = ((budget - 500) / (50000 - 500)) * 100;

  return (
    <div className="wrap">
      <div className="top">
        <Link className="brand" href="/">
          <span className="brand-mark">i</span>
          <span>InfluenceIQ</span>
        </Link>
        <div className="progress" id="progress">
          <div
            className={`step-dot ${step === 1 ? "active" : ""} ${
              step > 1 ? "done" : ""
            }`}
            onClick={() => go(1)}
            style={{ cursor: "pointer" }}
          >
            <span className="num">1</span>
            <span className="step-label">Your brand</span>
          </div>
          <div className={`bar ${step > 1 ? "done" : ""}`}></div>
          <div
            className={`step-dot ${step === 2 ? "active" : ""} ${
              step > 2 ? "done" : ""
            }`}
            onClick={() => go(2)}
            style={{ cursor: "pointer" }}
          >
            <span className="num">2</span>
            <span className="step-label">Goals</span>
          </div>
          <div className={`bar ${step > 2 ? "done" : ""}`}></div>
          <div
            className={`step-dot ${step === 3 ? "active" : ""}`}
            onClick={() => go(3)}
            style={{ cursor: "pointer" }}
          >
            <span className="num">3</span>
            <span className="step-label">Platforms</span>
          </div>
        </div>
        <Link className="quit" href="/dashboard?welcome=1">
          Skip for now
        </Link>
      </div>

      <div className="body">
        <div className="card">
          {/* STEP 1 */}
          <section className={`step-view ${step === 1 ? "active" : ""}`} id="s1">
            <span className="eyebrow">Step 1 of 3</span>
            <h1>
              Tell us about your <span className="ac">brand.</span>
            </h1>
            <p className="sub">
              We use this to calibrate match scoring and surface creators whose
              audiences fit yours.
            </p>
            <div className="field">
              <label>Brand name</label>
              <input defaultValue="Northwind Outdoor" />
            </div>
            <div className="grid2">
              <div className="field">
                <label>Industry</label>
                <select defaultValue="Outdoor & activewear">
                  <option>Outdoor & activewear</option>
                  <option>Beauty & skincare</option>
                  <option>Food & beverage</option>
                  <option>Tech & SaaS</option>
                  <option>Fashion & apparel</option>
                  <option>Fitness & wellness</option>
                  <option>Travel & hospitality</option>
                  <option>Gaming & entertainment</option>
                </select>
              </div>
              <div className="field">
                <label>Company size</label>
                <select defaultValue="11–50">
                  <option>1–10</option>
                  <option>11–50</option>
                  <option>51–200</option>
                  <option>201–1000</option>
                  <option>1000+</option>
                </select>
              </div>
            </div>
            <div className="field">
              <label>Country</label>
              <select defaultValue="Canada">
                <option>United States</option>
                <option>Canada</option>
                <option>United Kingdom</option>
                <option>India</option>
                <option>Bangladesh</option>
                <option>Global</option>
              </select>
            </div>
            <div className="actions">
              <span></span>
              <button className="next" onClick={() => go(2)}>
                Next
                <span
                  style={{
                    fontFamily: "Instrument Serif, serif",
                    fontStyle: "italic",
                  }}
                >
                  →
                </span>
              </button>
            </div>
          </section>

          {/* STEP 2 */}
          <section className={`step-view ${step === 2 ? "active" : ""}`} id="s2">
            <span className="eyebrow">Step 2 of 3</span>
            <h1>
              What are your <span className="ac">campaign goals?</span>
            </h1>
            <p className="sub">
              Pick as many as apply. We&apos;ll prioritise creators with proven
              outcomes against these.
            </p>
            <div className="chips" id="goals">
              <span
                className={`gchip ${goals.includes("awareness") ? "on" : ""}`}
                onClick={() => toggleGoal("awareness")}
              >
                Brand Awareness{" "}
                <span className="check">
                  <svg viewBox="0 0 16 12">
                    <path
                      d="M1 6 L6 11 L15 1"
                      stroke="white"
                      strokeWidth="2.4"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
              </span>
              <span
                className={`gchip ${goals.includes("launch") ? "on" : ""}`}
                onClick={() => toggleGoal("launch")}
              >
                Product Launch{" "}
                <span className="check">
                  <svg viewBox="0 0 16 12">
                    <path
                      d="M1 6 L6 11 L15 1"
                      stroke="white"
                      strokeWidth="2.4"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
              </span>
              <span
                className={`gchip ${goals.includes("sales") ? "on" : ""}`}
                onClick={() => toggleGoal("sales")}
              >
                Sales{" "}
                <span className="check">
                  <svg viewBox="0 0 16 12">
                    <path
                      d="M1 6 L6 11 L15 1"
                      stroke="white"
                      strokeWidth="2.4"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
              </span>
              <span
                className={`gchip ${goals.includes("event") ? "on" : ""}`}
                onClick={() => toggleGoal("event")}
              >
                Event Promotion{" "}
                <span className="check">
                  <svg viewBox="0 0 16 12">
                    <path
                      d="M1 6 L6 11 L15 1"
                      stroke="white"
                      strokeWidth="2.4"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
              </span>
              <span
                className={`gchip ${goals.includes("ltp") ? "on" : ""}`}
                onClick={() => toggleGoal("ltp")}
              >
                Long-term Partnership{" "}
                <span className="check">
                  <svg viewBox="0 0 16 12">
                    <path
                      d="M1 6 L6 11 L15 1"
                      stroke="white"
                      strokeWidth="2.4"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
              </span>
            </div>
            <div className="actions">
              <button className="back" onClick={() => go(1)}>
                ← Back
              </button>
              <button className="next" onClick={() => go(3)}>
                Next
                <span
                  style={{
                    fontFamily: "Instrument Serif, serif",
                    fontStyle: "italic",
                  }}
                >
                  →
                </span>
              </button>
            </div>
          </section>

          {/* STEP 3 */}
          <section className={`step-view ${step === 3 ? "active" : ""}`} id="s3">
            <span className="eyebrow">Step 3 of 3</span>
            <h1>
              Which platforms do you <span className="ac">focus on?</span>
            </h1>
            <p className="sub">
              Toggle the platforms you care about and set a typical monthly
              budget.
            </p>
            <div className="pgrid" id="platforms">
              <div
                className={`pcard ${platforms.includes("instagram") ? "on" : ""}`}
                onClick={() => togglePlatform("instagram")}
              >
                <span
                  className="icon"
                  style={{
                    background:
                      "linear-gradient(135deg,#f58529,#dd2a7b 50%,#8134af 80%,#515bd4)",
                  }}
                >
                  <svg
                    viewBox="0 0 24 24"
                    width="16"
                    height="16"
                    fill="none"
                    stroke="white"
                    strokeWidth="2"
                  >
                    <rect x="3" y="3" width="18" height="18" rx="5" />
                    <circle cx="12" cy="12" r="4" />
                    <circle cx="17.5" cy="6.5" r="0.5" fill="white" />
                  </svg>
                </span>
                <div>
                  <div className="nm">Instagram</div>
                  <div className="desc">Reels, carousels, stories</div>
                </div>
                <span className="tick">
                  <svg viewBox="0 0 16 12">
                    <path
                      d="M1 6 L6 11 L15 1"
                      stroke="white"
                      strokeWidth="2.4"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
              </div>
              <div
                className={`pcard ${platforms.includes("tiktok") ? "on" : ""}`}
                onClick={() => togglePlatform("tiktok")}
              >
                <span className="icon" style={{ background: "#0a0b10" }}>
                  <svg viewBox="0 0 20 22" width="14" height="14" fill="white">
                    <path d="M14.5 1c.4 1.8 1.5 3.4 3 4.4 1.1.7 2.5 1.1 3.9 1.1V11c-1.6 0-3.2-.4-4.6-1.1-.6-.3-1.2-.7-1.7-1.1v6.6c0 4.1-3.4 7.5-7.5 7.5-1.6 0-3.1-.5-4.3-1.4-1.9-1.4-3.2-3.7-3.2-6.2 0-4.1 3.4-7.5 7.5-7.5.4 0 .9 0 1.3.1v4.4c-.4-.1-.8-.2-1.3-.2-1.7 0-3.1 1.4-3.1 3.1s1.4 3.2 3.2 3.2 3.2-1.4 3.2-3.1V1h3.6z" />
                  </svg>
                </span>
                <div>
                  <div className="nm">TikTok</div>
                  <div className="desc">Short-form, trending</div>
                </div>
                <span className="tick">
                  <svg viewBox="0 0 16 12">
                    <path
                      d="M1 6 L6 11 L15 1"
                      stroke="white"
                      strokeWidth="2.4"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
              </div>
              <div
                className={`pcard ${platforms.includes("youtube") ? "on" : ""}`}
                onClick={() => togglePlatform("youtube")}
              >
                <span className="icon" style={{ background: "#ff0033" }}>
                  <svg viewBox="0 0 24 18" width="16" height="12" fill="white">
                    <path d="M23.5 3.5a3 3 0 0 0-2.1-2.1C19.5 1 12 1 12 1s-7.5 0-9.4.4A3 3 0 0 0 .5 3.5C.1 5.4.1 9 .1 9s0 3.6.4 5.5a3 3 0 0 0 2.1 2.1C4.5 17 12 17 12 17s7.5 0 9.4-.4a3 3 0 0 0 2.1-2.1c.4-1.9.4-5.5.4-5.5s0-3.6-.4-5.5zM9.5 12.5v-7L15.5 9l-6 3.5z" />
                  </svg>
                </span>
                <div>
                  <div className="nm">YouTube</div>
                  <div className="desc">Long-form, Shorts</div>
                </div>
                <span className="tick">
                  <svg viewBox="0 0 16 12">
                    <path
                      d="M1 6 L6 11 L15 1"
                      stroke="white"
                      strokeWidth="2.4"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
              </div>
              <div
                className={`pcard ${platforms.includes("facebook") ? "on" : ""}`}
                onClick={() => togglePlatform("facebook")}
              >
                <span className="icon" style={{ background: "#1877f2" }}>
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="white">
                    <path d="M14 9V7c0-1 .5-2 2-2h2V1h-3c-3 0-5 2-5 5v3H7v4h3v9h4v-9h3l1-4h-4z" />
                  </svg>
                </span>
                <div>
                  <div className="nm">Facebook</div>
                  <div className="desc">Reels, communities</div>
                </div>
                <span className="tick">
                  <svg viewBox="0 0 16 12">
                    <path
                      d="M1 6 L6 11 L15 1"
                      stroke="white"
                      strokeWidth="2.4"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
              </div>
            </div>

            <div className="budget-box">
              <div className="budget-head">
                <div className="l">Monthly budget</div>
                <div className="v">
                  $<span id="bv">{budget.toLocaleString()}</span>
                  <span className="u">/mo</span>
                </div>
              </div>
              <div className="slider">
                <div
                  className="fill"
                  id="fill"
                  style={{ width: `${budgetPct}%` }}
                ></div>
                <div
                  className="thumb"
                  id="thumb"
                  style={{ left: `${budgetPct}%` }}
                ></div>
                <input
                  type="range"
                  id="brange"
                  min="500"
                  max="50000"
                  step="500"
                  value={budget}
                  onChange={handleBudgetChange}
                />
              </div>
              <div className="scale">
                <span>$500</span>
                <span>$10K</span>
                <span>$25K</span>
                <span>$50K+</span>
              </div>
            </div>

            <div className="actions">
              <button className="back" onClick={() => go(2)}>
                ← Back
              </button>
              <button className="next" onClick={finish}>
                Finish Setup
                <span
                  style={{
                    fontFamily: "Instrument Serif, serif",
                    fontStyle: "italic",
                  }}
                >
                  →
                </span>
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
