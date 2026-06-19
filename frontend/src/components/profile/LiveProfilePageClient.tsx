"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  getCampaign,
  getCampaignInfluencer,
  type CampaignSummary,
} from "@/lib/api";
import type { InfluencerRecommendation } from "@/types/influencer";
import {
  avatarFromName,
  estimateRateNumber,
  estimateViews,
  extractCategory,
  extractLocation,
  extractTags,
  formatCompactNumber,
  formatPercent,
  titleize,
} from "@/lib/influencerPresentation";
import ProfileInteractions from "./ProfileInteractions";

type LiveProfilePageClientProps = {
  campaignId?: string;
  influencerId: string;
};

const platformLinks = (item: InfluencerRecommendation) => {
  const identity = item.sourcePayload.identity;
  if (identity && typeof identity === "object") {
    const url = (identity as Record<string, unknown>).canonical_profile_url;
    if (typeof url === "string" && url) {
      return [url];
    }
  }
  return item.citations.slice(0, 3);
};

export default function LiveProfilePageClient({
  campaignId,
  influencerId,
}: LiveProfilePageClientProps) {
  const missingCampaignId = !campaignId;
  const [campaign, setCampaign] = useState<CampaignSummary | null>(null);
  const [influencer, setInfluencer] = useState<InfluencerRecommendation | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(!missingCampaignId);

  useEffect(() => {
    if (missingCampaignId) {
      return;
    }

    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        const [campaignData, influencerData] = await Promise.all([
          getCampaign(campaignId),
          getCampaignInfluencer(campaignId, influencerId),
        ]);
        if (cancelled) return;
        setCampaign(campaignData);
        if (!influencerData) {
          setError("Creator not found in this campaign shortlist.");
        } else {
          setInfluencer(influencerData);
          setError("");
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Unable to load profile");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [campaignId, influencerId, missingCampaignId]);

  const profile = useMemo(() => {
    if (!influencer) return null;

    const links = platformLinks(influencer);
    const engagement = influencer.sourcePayload.engagement;
    const engagementData =
      engagement && typeof engagement === "object"
        ? (engagement as Record<string, unknown>)
        : {};
    const profiles = Array.isArray(influencer.sourcePayload.profiles)
      ? (influencer.sourcePayload.profiles as Array<Record<string, unknown>>)
      : [];

    return {
      name: influencer.name,
      handle: influencer.handle || "@unknown",
      platform: titleize(influencer.platform),
      avatar: avatarFromName(influencer.name),
      verified: influencer.trustGrade === "A+" || influencer.trustGrade === "A",
      bio:
        (profiles[0]?.bio as string) ||
        "Profile bio was not available from the enrichment source.",
      category: extractCategory(influencer),
      tags: extractTags(influencer),
      location: extractLocation(influencer),
      followers: formatCompactNumber(influencer.followers),
      avgViews: formatCompactNumber(estimateViews(influencer.followers, influencer.engagementRate)),
      engagement: formatPercent(influencer.engagementRate),
      postsPerMonth: Number(engagementData.sample_size ?? 0),
      rate: estimateRateNumber(influencer),
      links,
      citations: influencer.citations,
      brandSafetyFlags: influencer.brandSafetyFlags,
      trustGrade: influencer.trustGrade,
      matchScore: Math.round(influencer.matchScore),
      sampleSize: Number(engagementData.sample_size ?? 0),
      avgLikes: Number(engagementData.average_likes ?? 0),
      avgComments: Number(engagementData.average_comments ?? 0),
      avgShares: Number(engagementData.average_shares ?? 0),
      avgViewsRaw: Number(engagementData.average_views ?? 0),
    };
  }, [influencer]);

  if (missingCampaignId) {
    return (
      <div className="panel">
        <p>A campaignId is required to load a live creator profile.</p>
        <Link className="back-link" href="/discover">
          Back to discover
        </Link>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="panel">
        Loading creator profile...
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="panel">
        <p>{error || "Creator profile unavailable."}</p>
        <Link className="back-link" href={campaignId ? `/discover?campaignId=${encodeURIComponent(campaignId)}` : "/discover"}>
          Back to discover
        </Link>
      </div>
    );
  }

  return (
    <>
      <Link
        className="back-link"
        href={campaignId ? `/discover?campaignId=${encodeURIComponent(campaignId)}` : "/discover"}
      >
        <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" style={{ width: "14px", height: "14px" }}>
          <path d="M15 6l-6 6 6 6" />
        </svg>
        Back to Discover
      </Link>

      <div className="layout">
        <div>
          <div className="panel">
            <div className="profile-head">
              <div className="pfp">
                {profile.avatar}
                {profile.verified ? (
                  <span className="verified" title="Verified creator">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
                      <circle cx="12" cy="12" r="9" />
                    </svg>
                  </span>
                ) : null}
              </div>
              <div className="name-row">
                <h1>{profile.name}</h1>
                <div className="handle">{profile.handle}</div>
                <div className="platforms">
                  {profile.links.map((link) => (
                    <a key={link} className="pf pf-yt" href={link} target="_blank" rel="noreferrer">
                      {new URL(link).hostname.replace(/^www\./, "")}
                    </a>
                  ))}
                </div>
              </div>
            </div>

            <p className="bio">{profile.bio}</p>

            <div className="tags">
              <span className="tag violet">{profile.category}</span>
              {profile.tags.map((tag) => (
                <span className="tag" key={tag}>
                  {tag}
                </span>
              ))}
            </div>

            <div className="meta-row">
              <div className="item">
                <span className="lab">Location</span>
                <span>{profile.location}</span>
              </div>
              <div className="item">
                <span className="lab">Platform</span>
                <span>{profile.platform}</span>
              </div>
              <div className="item">
                <span className="lab">Campaign</span>
                <span>{campaign?.product ?? "Live shortlist"}</span>
              </div>
            </div>

            <div className="stats">
              <div>
                <div className="lbl">Followers</div>
                <div className="val">{profile.followers}</div>
              </div>
              <div>
                <div className="lbl">Avg Views</div>
                <div className="val">{profile.avgViews}</div>
              </div>
              <div>
                <div className="lbl">Engagement</div>
                <div className="val eng">{profile.engagement}</div>
              </div>
              <div>
                <div className="lbl">Sample size</div>
                <div className="val">{profile.sampleSize}</div>
              </div>
            </div>

            <div className="rate-card">
              <div className="lab">Estimated rate per post</div>
              <div className="v">${profile.rate.toLocaleString()}</div>
              <div className="note">Derived from shortlist data and follower band.</div>
            </div>

            <div className="contact">
              {profile.links.map((link) => (
                <a key={link} className="contact-item" href={link} target="_blank" rel="noreferrer">
                  <span className="cico" style={{ background: "linear-gradient(135deg,var(--violet),var(--coral))" }}>
                    <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                      <path d="M10 14 21 3" />
                      <path d="M21 3h-7" />
                      <path d="M21 3v7" />
                      <path d="M14 10v11H3V10h11" />
                    </svg>
                  </span>
                  <div className="cv">
                    <div className="k">Profile link</div>
                    <div className="val">{link}</div>
                  </div>
                  <span className="arr">-&gt;</span>
                </a>
              ))}
            </div>
          </div>
        </div>

        <div>
          <section className="match-hero">
            <div className="match-ring" aria-hidden="true">
              <svg width="130" height="130" viewBox="0 0 130 130">
                <defs>
                  <linearGradient id="matchG" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="oklch(0.74 0.18 30)" />
                    <stop offset="50%" stopColor="oklch(0.68 0.20 295)" />
                    <stop offset="100%" stopColor="oklch(0.78 0.15 215)" />
                  </linearGradient>
                </defs>
                <circle cx="65" cy="65" r="55" stroke="rgba(255,255,255,0.12)" strokeWidth="10" fill="none" />
                <circle cx="65" cy="65" r="55" stroke="url(#matchG)" strokeWidth="10" fill="none" strokeDasharray="345.5" strokeDashoffset={`${345.5 - 3.455 * profile.matchScore}`} strokeLinecap="round"></circle>
              </svg>
              <div className="center">
                <div>
                  <div className="num">
                    {profile.matchScore}
                    <span className="pct">%</span>
                  </div>
                  <div className="label">AI Match</div>
                </div>
              </div>
            </div>
            <div>
              <h2>
                Live shortlist profile for <span className="accent">{campaign?.brand ?? "your campaign"}</span>.
              </h2>
              <p>
                This profile is rendered from backend enrichment, crawl provenance, and scoring output for the current campaign.
              </p>
              <div className="badge-row">
                <span className="mb good">Grade {profile.trustGrade}</span>
                <span className="mb">{profile.platform}</span>
                <span className="mb">{profile.sampleSize} sampled posts</span>
                <span className="mb">{profile.brandSafetyFlags.length ? "Review flags" : "Brand safe"}</span>
              </div>
            </div>
          </section>

          <section className="panel">
            <div className="panel-head">
              <h3>
                <span className="pin"></span>Why This Creator Ranked
              </h3>
              <span className="meta">Derived from live backend scoring</span>
            </div>
            <div className="reasons">
              <div className="reason">
                <div className="body">
                  <div className="t">Campaign score: {profile.matchScore}%</div>
                  <div className="d">The backend shortlist scored this creator against relevance, credibility, engagement, sentiment, and brand-safety signals.</div>
                </div>
              </div>
              <div className="reason">
                <div className="body">
                  <div className="t">Engagement sample from {profile.sampleSize} recent posts</div>
                  <div className="d">
                    Avg views {formatCompactNumber(profile.avgViewsRaw)}, likes {formatCompactNumber(profile.avgLikes)}, comments {formatCompactNumber(profile.avgComments)}, shares {formatCompactNumber(profile.avgShares)}.
                  </div>
                </div>
              </div>
              <div className="reason">
                <div className="body">
                  <div className="t">Source-backed identity</div>
                  <div className="d">The profile keeps crawl citations and platform enrichment payloads attached to the campaign result.</div>
                </div>
              </div>
              <div className="reason">
                <div className="body">
                  <div className="t">Brand-safety review</div>
                  <div className="d">
                    {profile.brandSafetyFlags.length
                      ? profile.brandSafetyFlags.join(", ")
                      : "No deterministic brand-safety flags were attached to this result."}
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="panel">
            <div className="panel-head">
              <h3>
                <span className="pin"></span>Supporting Sources
              </h3>
              <span className="meta">{profile.citations.length} citations</span>
            </div>
            <div className="comments">
              {profile.citations.length ? (
                profile.citations.map((citation) => (
                  <div className="comment" key={citation}>
                    <div>
                      <div className="who">{citation}</div>
                      <div className="txt">Crawl or profile source used in this campaign result.</div>
                    </div>
                    <span className="pill pill-neu">Source</span>
                  </div>
                ))
              ) : (
                <div className="comment">
                  <div>
                    <div className="who">No citations recorded</div>
                    <div className="txt">The backend did not return supporting source URLs for this profile.</div>
                  </div>
                </div>
              )}
            </div>
          </section>

          <ProfileInteractions />
        </div>
      </div>
    </>
  );
}
