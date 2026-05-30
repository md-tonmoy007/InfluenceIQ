"use client";

import React from "react";
import Link from "next/link";
import { discoverCreators } from "@/data/creators";
import SaveToListPopover from "@/components/ui/SaveToListPopover";

const platformGlyphs: Record<string, React.ReactNode> = {
  instagram: (
    <span className="platform pf-ig" title="Instagram">
      <svg
        width="11"
        height="11"
        viewBox="0 0 24 24"
        fill="none"
        stroke="white"
        strokeWidth="2"
      >
        <rect x="3" y="3" width="18" height="18" rx="5" />
        <circle cx="12" cy="12" r="4" />
        <circle cx="17.5" cy="6.5" r="0.5" fill="white" />
      </svg>
    </span>
  ),
  youtube: (
    <span className="platform pf-yt" title="YouTube">
      <svg width="11" height="9" viewBox="0 0 24 18" fill="white">
        <path d="M23.5 3.5a3 3 0 0 0-2.1-2.1C19.5 1 12 1 12 1s-7.5 0-9.4.4A3 3 0 0 0 .5 3.5C.1 5.4.1 9 .1 9s0 3.6.4 5.5a3 3 0 0 0 2.1 2.1C4.5 17 12 17 12 17s7.5 0 9.4-.4a3 3 0 0 0 2.1-2.1c.4-1.9.4-5.5.4-5.5s0-3.6-.4-5.5zM9.5 12.5v-7L15.5 9l-6 3.5z" />
      </svg>
    </span>
  ),
  tiktok: (
    <span className="platform pf-tt" title="TikTok">
      <svg width="9" height="10" viewBox="0 0 20 22" fill="white">
        <path d="M14.5 1c.4 1.8 1.5 3.4 3 4.4 1.1.7 2.5 1.1 3.9 1.1V11c-1.6 0-3.2-.4-4.6-1.1-.6-.3-1.2-.7-1.7-1.1v6.6c0 4.1-3.4 7.5-7.5 7.5-1.6 0-3.1-.5-4.3-1.4-1.9-1.4-3.2-3.7-3.2-6.2 0-4.1 3.4-7.5 7.5-7.5.4 0 .9 0 1.3.1v4.4c-.4-.1-.8-.2-1.3-.2-1.7 0-3.1 1.4-3.1 3.1s1.4 3.2 3.2 3.2 3.2-1.4 3.2-3.1V1h3.6z" />
      </svg>
    </span>
  ),
  facebook: (
    <span className="platform pf-fb" title="Facebook">
      <svg width="9" height="9" viewBox="0 0 24 24" fill="white">
        <path d="M14 9V7c0-1 .5-2 2-2h2V1h-3c-3 0-5 2-5 5v3H7v4h3v9h4v-9h3l1-4h-4z" />
      </svg>
    </span>
  ),
};

const platformName: Record<string, string> = {
  instagram: "Instagram",
  youtube: "YouTube",
  tiktok: "TikTok",
  facebook: "Facebook",
};

const tierClass: Record<string, string> = {
  Rising: "tier-rising",
  Established: "tier-established",
  Premium: "tier-premium",
};

const matchClass = (m: number) =>
  m >= 92 ? "match-high" : m >= 85 ? "match-mid" : "match-low";

export default function DiscoverGrid() {
  return (
    <div className="grid" id="grid">
      {discoverCreators.map((c, i) => (
        <article
          className={`card ${c.glow}`}
          key={c.id}
          style={{ animationDelay: `${0.04 * i}s` }}
        >
          <div className="card-top">
            <div className={`card-av ${c.avatarClass}`}>
              {c.avatar}
              {platformGlyphs[c.platform]}
            </div>
            <div className="card-id">
              <div className="card-name">{c.name}</div>
              <div className="card-handle">
                <span className="pname">{platformName[c.platform]}</span>
                <span className="sep">·</span>
                <span>{c.handle}</span>
              </div>
            </div>
            <span className={`match-chip ${matchClass(c.match)}`}>
              <svg viewBox="0 0 12 12" fill="currentColor">
                <path d="M6 1l1.5 3.4L11 5l-2.5 2.4L9 11 6 9.2 3 11l.5-3.6L1 5l3.5-.6L6 1z" />
              </svg>
              {c.match}% match
            </span>
          </div>

          <div className="card-tags">
            <span className={`tag tag-tier ${tierClass[c.tier]}`}>{c.tier}</span>
            {c.tags.map((t) => (
              <span className="tag" key={t}>
                {t}
              </span>
            ))}
            <span className="tag">{c.category}</span>
          </div>

          <div className="card-stats">
            <div>
              <div className="lbl">Followers</div>
              <div className="val">{c.followers}</div>
            </div>
            <div>
              <div className="lbl">Engagement</div>
              <div className="val eng">{c.engagement}</div>
            </div>
            <div>
              <div className="lbl">Rate / post</div>
              <div className="val">{c.rate}</div>
            </div>
          </div>

          <div className="card-actions">
            <Link className="btn-card btn-view" href="/profile/lila-park">
              View Profile
              <svg
                className="i"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                style={{ width: "14px", height: "14px" }}
              >
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </Link>
            <SaveToListPopover>
              <button
                className="btn-card btn-save"
                type="button"
                aria-label="Save to list"
                title="Save to list"
              >
                <svg
                  className="i"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  style={{ width: "15px", height: "15px" }}
                >
                  <path d="M19 21l-7-4.5L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16Z" />
                </svg>
              </button>
            </SaveToListPopover>
          </div>
        </article>
      ))}
    </div>
  );
}
