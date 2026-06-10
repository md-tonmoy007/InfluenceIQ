"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { CSSProperties } from "react";

export default function NotificationMenu() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [hovered, setHovered] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (wrapperRef.current && !wrapperRef.current.contains(target)) {
        setOpen(false);
      }
    };
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  const popStyle: CSSProperties = {
    position: "absolute",
    top: "calc(100% + 8px)",
    right: 0,
    width: "min(340px, calc(100vw - 28px))",
    background: "#fff",
    border: "1px solid var(--line,#e6e3da)",
    borderRadius: "14px",
    boxShadow: "0 24px 60px -22px rgba(15,17,22,0.28)",
    overflow: "hidden",
    zIndex: 50,
    fontFamily: "Geist,system-ui,sans-serif",
    display: open ? "block" : "none",
  };

  const itemStyle: CSSProperties = {
    padding: "14px 16px",
    display: "flex",
    gap: "12px",
    background: hovered
      ? "oklch(0.94 0.05 285)"
      : "linear-gradient(180deg,oklch(0.96 0.04 285),#fff)",
    cursor: "pointer",
    transition: "background .2s",
  };

  return (
    <div className="notif-menu" ref={wrapperRef} style={{ position: "relative" }}>
      <button
        className="icon-btn"
        id="notif"
        title="Notifications"
        aria-label="Notifications"
        style={{ position: "relative" }}
        onClick={() => setOpen((prev) => !prev)}
      >
        <svg
          className="i"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
        >
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 7 3 9H3c0-2 3-2 3-9Z" />
          <path d="M10 21a2 2 0 0 0 4 0" />
        </svg>
        <span
          style={{
            position: "absolute",
            top: "7px",
            right: "7px",
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            background: "var(--coral)",
            border: "1.5px solid #fff",
            animation: "pulseDot 2s ease-out infinite",
          }}
        ></span>
      </button>

      <div style={popStyle}>
        <div
          style={{
            padding: "14px 16px",
            borderBottom: "1px solid #efece4",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ fontSize: "14px", fontWeight: 500 }}>
            Notifications
          </div>
          <span
            style={{
              fontFamily: "JetBrains Mono,monospace",
              fontSize: "10px",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "#6c6f7a",
            }}
          >
            1 NEW
          </span>
        </div>

        <div
          role="button"
          tabIndex={0}
          style={itemStyle}
          onClick={() => {
            setOpen(false);
            router.push("/shortlist");
          }}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "50%",
              background:
                "linear-gradient(135deg,oklch(0.58 0.22 285),oklch(0.74 0.18 30))",
              display: "grid",
              placeItems: "center",
              color: "#fff",
              flexShrink: 0,
              fontFamily: "Instrument Serif,serif",
              fontStyle: "italic",
            }}
          >
            ✦
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: "13px", fontWeight: 500, lineHeight: 1.35 }}>
              Your <span style={{ fontFamily: "Instrument Serif,serif", fontStyle: "italic" }}>
                Ramadan Campaign
              </span>{" "}
              shortlist is ready
            </div>
            <div style={{ fontSize: "11.5px", color: "#6c6f7a", marginTop: "4px" }}>
              14 ranked matches · 12 minutes ago
            </div>
          </div>
          <span
            style={{
              width: "7px",
              height: "7px",
              borderRadius: "50%",
              background: "oklch(0.74 0.18 30)",
              flexShrink: 0,
              marginTop: "6px",
            }}
          ></span>
        </div>

        <div
          style={{
            padding: "10px 16px",
            borderTop: "1px solid #efece4",
            textAlign: "center",
            color: "oklch(0.32 0.18 285)",
            fontSize: "12.5px",
            fontWeight: 500,
            cursor: "pointer",
          }}
        >
          View all notifications →
        </div>
      </div>
    </div>
  );
}
