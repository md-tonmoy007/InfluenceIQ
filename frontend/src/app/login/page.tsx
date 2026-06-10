"use client";

import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import "../signup.css";

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState("");

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (loading) return;

    const form = new FormData(event.currentTarget);
    setLoading(true);
    setError("");

    try {
      await login({
        email: String(form.get("email") ?? ""),
        password: String(form.get("password") ?? ""),
      });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to log in.");
      setLoading(false);
    }
  };

  return (
    <div className="auth">
      <div className="form-side">
        <Link className="brand" href="/">
          <span className="brand-mark">i</span>
          <span>InfluenceIQ</span>
        </Link>

        <h1>
          Welcome <span className="ac">back.</span>
        </h1>
        <p className="sub">
          Log in to view your workspace, campaign briefs, and influencer
          recommendations.
        </p>

        <form className="form" onSubmit={handleSubmit}>
          <div className="field">
            <label>Work email</label>
            <input name="email" type="email" required defaultValue="elena@northwind.co" />
          </div>

          <div className="field">
            <label>Password</label>
            <input name="password" type="password" required defaultValue="password123" />
          </div>

          {error ? (
            <p className="terms" style={{ color: "oklch(0.45 0.20 25)" }}>
              {error}
            </p>
          ) : null}

          <button className="submit" type="submit" disabled={loading}>
            {loading ? "Logging in..." : "Log In"}{" "}
            <span style={{ fontFamily: "Instrument Serif, serif", fontStyle: "italic" }}>
              -&gt;
            </span>
          </button>
        </form>

        <div className="foot">
          Need an account? <Link href="/signup">Create one</Link>
        </div>
      </div>

      <div className="vis">
        <div>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: "rgba(255,255,255,0.08)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "999px",
              padding: "5px 12px 5px 6px",
              fontSize: "12px",
              color: "rgba(255,255,255,0.85)",
              marginBottom: "24px",
            }}
          >
            <span
              style={{
                background:
                  "linear-gradient(135deg,oklch(0.58 0.22 285),oklch(0.74 0.18 30))",
                color: "#fff",
                borderRadius: "999px",
                padding: "3px 10px",
                fontFamily: "JetBrains Mono, monospace",
                fontSize: "10px",
                letterSpacing: "0.06em",
                textTransform: "uppercase",
              }}
            >
              session
            </span>
            Cookie-backed account access
          </span>
          <h2>
            Your campaigns.
            <br />
            Your results.
          </h2>
          <p>
            InfluenceIQ keeps campaign data tied to the signed-in account, so
            another user cannot open your briefs or live matching stream.
          </p>
        </div>

        <div className="stat-strip">
          <div className="s">
            <div className="l">Auth</div>
            <div className="v">JWT</div>
          </div>
          <div className="s">
            <div className="l">Cookie</div>
            <div className="v">HttpOnly</div>
          </div>
          <div className="s">
            <div className="l">Scope</div>
            <div className="v">Owner</div>
          </div>
        </div>
      </div>
    </div>
  );
}
