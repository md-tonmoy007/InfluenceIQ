"use client";

import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import "../signup.css";

export default function SignupPage() {
  const router = useRouter();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    router.push("/onboarding");
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
          Free forever — no credit card. Index your first campaign in five
          minutes.
        </p>

        <div className="social">
          <button className="sb" type="button">
            <svg viewBox="0 0 48 48">
              <path
                fill="#4285F4"
                d="M24 9.5c3.5 0 6.6 1.2 9 3.5l6.7-6.7C35.4 2.5 30 0 24 0 14.7 0 6.8 5.3 2.8 13l7.9 6.1C12.5 13.6 17.8 9.5 24 9.5z"
              />
              <path
                fill="#34A853"
                d="M46.9 24.5c0-1.7-.2-3.3-.4-4.9H24v9.3h12.8c-.6 3-2.2 5.5-4.7 7.2l7.3 5.7c4.3-4 6.8-9.8 6.8-17.3z"
              />
              <path
                fill="#FBBC05"
                d="M10.7 28.7c-.5-1.5-.8-3-.8-4.7s.3-3.2.8-4.7l-7.9-6.1C1.1 16.3 0 20 0 24s1.1 7.7 2.8 10.8l7.9-6.1z"
              />
              <path
                fill="#EA4335"
                d="M24 48c6 0 11.1-2 14.8-5.4l-7.3-5.7c-2 1.4-4.6 2.2-7.5 2.2-6.2 0-11.5-4.2-13.3-9.7l-7.9 6.1C6.8 42.7 14.7 48 24 48z"
              />
            </svg>
            Continue with Google
          </button>
          <button className="sb" type="button">
            <svg viewBox="0 0 24 24" fill="#0A66C2">
              <path d="M20.5 2h-17A1.5 1.5 0 002 3.5v17A1.5 1.5 0 003.5 22h17a1.5 1.5 0 001.5-1.5v-17A1.5 1.5 0 0020.5 2zM8 19H5v-9h3zM6.5 8.25A1.75 1.75 0 118.3 6.5a1.78 1.78 0 01-1.8 1.75zM19 19h-3v-4.74c0-1.42-.6-1.93-1.38-1.93A1.74 1.74 0 0013 14.19a.66.66 0 000 .14V19h-3v-9h2.9v1.3a3.11 3.11 0 012.7-1.4c1.55 0 3.36.86 3.36 3.66z" />
            </svg>
            Continue with LinkedIn
          </button>
        </div>
        <div className="divider">
          <span>or sign up with email</span>
        </div>

        <form className="form" onSubmit={handleSubmit}>
          <div className="row">
            <div className="field">
              <label>Company name</label>
              <input required defaultValue="Northwind Outdoor" />
            </div>
            <div className="field">
              <label>Your name</label>
              <input required defaultValue="Elena Marchetti" />
            </div>
          </div>
          <div className="field">
            <label>Work email</label>
            <input type="email" required defaultValue="elena@northwind.co" />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" required defaultValue="••••••••••" />
          </div>
          <button className="submit" type="submit">
            Create Free Account{" "}
            <span
              style={{
                fontFamily: "Instrument Serif, serif",
                fontStyle: "italic",
              }}
            >
              →
            </span>
          </button>
          <p className="terms">
            By creating an account you agree to our <a href="#">Terms</a> and{" "}
            <a href="#">Privacy Policy</a>.
          </p>
        </form>

        <div className="foot">
          Already have an account? <Link href="/dashboard">Log in</Link>
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
              position: "relative",
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
              v3
            </span>
            AI matching across 2.4M creators
          </span>
          <h2>
            Match in <span className="ac">seconds.</span>
            <br />
            Launch in days.
          </h2>
          <p>
            Brand managers at 1,200+ companies use InfluenceIQ to skip the
            agency middleman and find creators who actually convert.
          </p>
        </div>

        <div className="stat-strip">
          <div className="s">
            <div className="l">Creators indexed</div>
            <div className="v">2.41M</div>
          </div>
          <div className="s">
            <div className="l">Avg match score</div>
            <div className="v">87.4</div>
          </div>
          <div className="s">
            <div className="l">Hours saved/mo</div>
            <div className="v">
              42
              <span
                style={{
                  fontSize: "13px",
                  color: "rgba(255,255,255,0.5)",
                  fontFamily: "Instrument Serif, serif",
                  fontStyle: "italic",
                }}
              >
                h
              </span>
            </div>
          </div>
        </div>

        <div className="quote">
          <div className="q">
            We shortlisted 14 creators in under three minutes — and 11 of them
            said yes.
          </div>
          <div className="a">Sarah Chen, Head of Growth at Halcyon Outdoor</div>
        </div>
      </div>
    </div>
  );
}
