"use client";

import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { signup } from "@/lib/api";
import { setTokens } from "@/lib/auth";
import "../signup.css";

export default function SignupPage() {
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
      const result = await signup({
        company_name: String(form.get("company_name") ?? ""),
        name: String(form.get("name") ?? ""),
        email: String(form.get("email") ?? ""),
        password: String(form.get("password") ?? ""),
      });
      setTokens(result.access_token, result.refresh_token);
      router.push("/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create account.");
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
          Start finding your <span className="ac">perfect</span> creators.
        </h1>
        <p className="sub">
          Create your workspace account. Your campaigns and results will stay
          private to this login.
        </p>

        <form className="form" onSubmit={handleSubmit}>
          <div className="row">
            <div className="field">
              <label>Company name</label>
              <input name="company_name" required defaultValue="Northwind Outdoor" />
            </div>
            <div className="field">
              <label>Your name</label>
              <input name="name" required defaultValue="Elena Marchetti" />
            </div>
          </div>

          <div className="field">
            <label>Work email</label>
            <input name="email" type="email" required defaultValue="elena@northwind.co" />
          </div>

          <div className="field">
            <label>Password</label>
            <input name="password" type="password" required minLength={8} defaultValue="password123" />
          </div>

          {error ? (
            <p className="terms" style={{ color: "oklch(0.45 0.20 25)" }}>
              {error}
            </p>
          ) : null}

          <button className="submit" type="submit" disabled={loading}>
            {loading ? "Creating account..." : "Create Free Account"}{" "}
            <span style={{ fontFamily: "Instrument Serif, serif", fontStyle: "italic" }}>
              -&gt;
            </span>
          </button>

          <p className="terms">
            By creating an account you agree to our <a href="#">Terms</a> and{" "}
            <a href="#">Privacy Policy</a>.
          </p>
        </form>

        <div className="foot">
          Already have an account? <Link href="/login">Log in</Link>
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
              secure
            </span>
            Private campaign workspace
          </span>
          <h2>
            Sign up once.
            <br />
            Own every brief.
          </h2>
          <p>
            Campaign briefs, matching progress, and saved recommendations are
            scoped to your authenticated account.
          </p>
        </div>

        <div className="stat-strip">
          <div className="s">
            <div className="l">Session</div>
            <div className="v">HttpOnly</div>
          </div>
          <div className="s">
            <div className="l">Campaign access</div>
            <div className="v">Owner</div>
          </div>
          <div className="s">
            <div className="l">Password storage</div>
            <div className="v">Hashed</div>
          </div>
        </div>
      </div>
    </div>
  );
}
