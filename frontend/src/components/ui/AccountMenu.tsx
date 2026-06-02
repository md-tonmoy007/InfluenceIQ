"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";

type AccountMenuProps = {
  orgName?: string;
};

export default function AccountMenu({ orgName = "Northwind Outdoor" }: AccountMenuProps) {
  const [open, setOpen] = useState(false);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
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
    width: "min(220px, calc(100vw - 28px))",
    background: "#fff",
    border: "1px solid #e6e3da",
    borderRadius: "12px",
    boxShadow: "0 24px 60px -22px rgba(15,17,22,0.28)",
    overflow: "hidden",
    zIndex: 50,
    fontFamily: "Geist,system-ui,sans-serif",
    display: open ? "block" : "none",
  };

  const itemStyle = (index: number, danger = false): CSSProperties => ({
    display: "flex",
    alignItems: "center",
    gap: "10px",
    padding: "10px 14px",
    fontSize: "13px",
    color: danger ? "oklch(0.40 0.20 25)" : "#2a2e3a",
    transition: "background .15s",
    background: hoveredIndex === index ? "#f4f2ec" : "transparent",
    borderTop: danger ? "1px solid #efece4" : undefined,
  });

  return (
    <div className="account-menu" ref={wrapperRef} style={{ position: "relative" }}>
      <div className="me" id="me" role="button" onClick={() => setOpen((prev) => !prev)}>
        <span className="av">EM</span>
        <div className="who">
          <div>Elena Marchetti</div>
          <div className="org">{orgName}</div>
        </div>
      </div>

      <div style={popStyle}>
        <div
          style={{
            padding: "12px 14px",
            borderBottom: "1px solid #efece4",
          }}
        >
          <div style={{ fontSize: "13px", fontWeight: 500 }}>Elena Marchetti</div>
          <div style={{ fontSize: "11.5px", color: "#6c6f7a" }}>
            elena@northwind.co
          </div>
        </div>

        <Link
          href="/settings"
          style={itemStyle(0)}
          onMouseEnter={() => setHoveredIndex(0)}
          onMouseLeave={() => setHoveredIndex(null)}
          onClick={() => setOpen(false)}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
          >
            <circle cx="12" cy="8" r="4" />
            <path d="M4 21a8 8 0 0 1 16 0" />
          </svg>
          Profile
        </Link>
        <Link
          href="/settings"
          style={itemStyle(1)}
          onMouseEnter={() => setHoveredIndex(1)}
          onMouseLeave={() => setHoveredIndex(null)}
          onClick={() => setOpen(false)}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
          >
            <circle cx="12" cy="12" r="3" />
            <path d="M19 12a7 7 0 0 0-.1-1.2l2-1.6-2-3.5-2.5.9a7 7 0 0 0-2.1-1.2L14 3h-4l-.3 2.4a7 7 0 0 0-2.1 1.2L5.1 5.7l-2 3.5 2 1.6A7 7 0 0 0 5 12c0 .4 0 .8.1 1.2l-2 1.6 2 3.5 2.5-.9c.6.5 1.4.9 2.1 1.2L10 21h4l.3-2.4a7 7 0 0 0 2.1-1.2l2.5.9 2-3.5-2-1.6c.1-.4.1-.8.1-1.2z" />
          </svg>
          Settings
        </Link>
        <Link
          href="/"
          style={itemStyle(2, true)}
          onMouseEnter={() => setHoveredIndex(2)}
          onMouseLeave={() => setHoveredIndex(null)}
          onClick={() => setOpen(false)}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
          >
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <path d="M16 17l5-5-5-5" />
            <path d="M21 12H9" />
          </svg>
          Log out
        </Link>
      </div>
    </div>
  );
}
