"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import DeepAnalysisTrigger from "@/components/profile/DeepAnalysisTrigger";
import SafetyFlagsPanel from "@/components/profile/SafetyFlagsPanel";
import ScoreBreakdownPanel from "@/components/profile/ScoreBreakdownPanel";
import ProfileInteractions from "./ProfileInteractions";
import {
  getCampaign,
  getInfluencerProfile,
  getInfluencerSafetyFlags,
  getInfluencerScores,
  getInfluencerVerifications,
  type CampaignSummary,
} from "@/lib/api";
import {
  avatarFromName,
  displayEngagement,
  displayFollowers,
  displayRate,
  displayViews,
  extractCategory,
  extractLocation,
  extractTags,
  titleize,
} from "@/lib/influencerPresentation";
import { shortlistHref } from "@/lib/routes";
import type { InfluencerRecommendation } from "@/types/influencer";

type LiveProfilePageClientProps = {
  campaignId?: string;
  influencerId: string;
};

const gradeFromScore = (score: number): InfluencerRecommendation["trustGrade"] => {
  if (score >= 90) return "A+";
  if (score >= 80) return "A";
  if (score >= 70) return "B";
  if (score >= 60) return "C";
  return "D";
};

const platformLinks = (platforms: Record<string, unknown>) =>
  Object.values(platforms)
    .filter((value): value is string => typeof value === "string" && value.length > 0)
    .slice(0, 3);

const citationHost = (url: string): string => {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "External source";
  }
};

export default function LiveProfilePageClient({
  campaignId,
  influencerId,
}: LiveProfilePageClientProps) {
  const [campaign, setCampaign] = useState<CampaignSummary | null>(null);
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);
  const [scores, setScores] = useState<Array<Record<string, unknown>>>([]);
  const [safetyFlags, setSafetyFlags] = useState<Array<Record<string, unknown>>>([]);
  const [verifications, setVerifications] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        setLoading(true);
        const requests: Promise<unknown>[] = [
          getInfluencerProfile(influencerId),
          getInfluencerScores(influencerId),
          getInfluencerSafetyFlags(influencerId),
          getInfluencerVerifications(influencerId),
        ];
        if (campaignId) {
          requests.push(getCampaign(campaignId));
        }

        const [profileData, scoreData, flagData, verificationData, campaignData] =
          await Promise.all(requests);

        if (cancelled) return;

        setProfile(profileData as Record<string, unknown>);
        setScores(scoreData as Array<Record<string, unknown>>);
        setSafetyFlags(flagData as Array<Record<string, unknown>>);
        setVerifications(verificationData as Array<Record<string, unknown>>);
        setCampaign((campaignData as CampaignSummary | undefined) ?? null);
        setError("");
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
  }, [campaignId, influencerId]);

  const campaignScore = useMemo(() => {
    if (campaignId) {
      return scores.find((score) => String(score.campaign_id) === campaignId) ?? null;
    }
    return scores[0] ?? null;
  }, [campaignId, scores]);

  const viewModel = useMemo(() => {
    if (!profile) return null;

    const name = String(profile.canonical_name ?? "Unknown creator");
    const handle = String(profile.primary_handle ?? "@unknown");
    const platform = titleize(String(profile.primary_platform ?? "instagram"));
    const platforms = (profile.platforms as Record<string, unknown> | undefined) ?? {};
    const finalScore = Number(campaignScore?.final_score ?? 0);
    const subScores = {
      relevance: Number(campaignScore?.relevance_score ?? 0),
      credibility: Number(campaignScore?.credibility_score ?? 0),
      engagement: Number(campaignScore?.engagement_score ?? 0),
      sentiment: Number(campaignScore?.sentiment_score ?? 0),
      brand_safety: Number(campaignScore?.brand_safety_score ?? 0),
    };
    const positiveReasons = (campaignScore?.positive_reasons as string[] | undefined) ?? [];
    const negativeReasons = (campaignScore?.negative_reasons as string[] | undefined) ?? [];
    const sourceProvenance =
      (campaignScore?.source_provenance as Array<Record<string, unknown>> | undefined) ?? [];
    const citations = sourceProvenance
      .map((source) => String(source.url ?? ""))
      .filter(Boolean);

    const recommendation: InfluencerRecommendation = {
      id: influencerId,
      name,
      handle,
      platform: String(profile.primary_platform ?? "instagram"),
      followers: Number(profile.follower_count ?? 0),
      engagementRate: Number(profile.engagement_rate ?? 0),
      rate: "",
      matchScore: finalScore,
      trustGrade: gradeFromScore(finalScore),
      brandSafetyFlags: safetyFlags.map((flag) => String(flag.reason ?? flag.risk_type ?? "Flag")),
      citations,
      subScores,
      scorePayload: {},
      sourcePayload: {
        platforms,
        credentials: profile.credentials ?? [],
      },
    };

    return {
      name,
      handle,
      platform,
      avatar: avatarFromName(name),
      verified: verifications.some((item) => item.verified === true),
      bio: "Canonical profile loaded from the influencer record.",
      category: String(profile.primary_category ?? extractCategory(recommendation)),
      tags: extractTags(recommendation),
      location: String(profile.primary_location ?? extractLocation(recommendation)),
      followers: displayFollowers(recommendation),
      avgViews: displayViews(recommendation),
      engagement: displayEngagement(recommendation),
      sampleSize: Number(profile.avg_views ?? 0) > 0 ? 12 : 0,
      rate: displayRate(recommendation),
      links: platformLinks(platforms),
      citations,
      trustGrade: gradeFromScore(finalScore),
      matchScore: Math.round(finalScore),
      subScores,
      positiveReasons,
      negativeReasons,
      followerCount: Number(profile.follower_count ?? 0),
    };
  }, [campaignScore, influencerId, profile, safetyFlags, verifications]);

  if (loading) {
    return (
      <div className="panel">
        Loading creator profile...
      </div>
    );
  }

  if (error || !viewModel) {
    return (
      <div className="panel">
        <p>{error || "Creator profile unavailable."}</p>
        <Link className="back-link" href={campaignId ? shortlistHref(campaignId) : "/discover"}>
          Back to shortlist
        </Link>
      </div>
    );
  }

  return (
    <>
      <Link
        className="back-link"
        href={campaignId ? shortlistHref(campaignId) : "/discover"}
      >
        <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" style={{ width: "14px", height: "14px" }}>
          <path d="M15 6l-6 6 6 6" />
        </svg>
        Back to {campaignId ? "shortlist" : "discover"}
      </Link>

      <div className="layout">
        <div>
          <div className="panel">
            <div className="profile-head">
              <div className="pfp">
                {viewModel.avatar}
                {viewModel.verified ? (
                  <span className="verified" title="Verified creator">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
                      <circle cx="12" cy="12" r="9" />
                    </svg>
                  </span>
                ) : null}
              </div>
              <div className="name-row">
                <h1>{viewModel.name}</h1>
                <div className="handle">{viewModel.handle}</div>
                <div className="platforms">
                  {viewModel.links.map((link) => (
                    <a key={link} className="pf pf-yt" href={link} target="_blank" rel="noreferrer">
                      {(() => {
                        try {
                          return new URL(link).hostname.replace(/^www\./, "");
                        } catch {
                          return link;
                        }
                      })()}
                    </a>
                  ))}
                </div>
              </div>
            </div>

            <p className="bio">{viewModel.bio}</p>

            <div className="tags">
              <span className="tag violet">{viewModel.category}</span>
              {viewModel.tags.map((tag) => (
                <span className="tag" key={tag}>
                  {tag}
                </span>
              ))}
            </div>

            <div className="meta-row">
              <div className="item">
                <span className="lab">Location</span>
                <span>{viewModel.location}</span>
              </div>
              <div className="item">
                <span className="lab">Platform</span>
                <span>{viewModel.platform}</span>
              </div>
              <div className="item">
                <span className="lab">Campaign</span>
                <span>{campaign?.product ?? (campaignId ? "Linked campaign" : "Not linked")}</span>
              </div>
            </div>

            <div className="stats">
              <div>
                <div className="lbl">Followers</div>
                <div className="val">{viewModel.followers}</div>
              </div>
              <div>
                <div className="lbl">Avg Views</div>
                <div className="val">{viewModel.avgViews}</div>
              </div>
              <div>
                <div className="lbl">Engagement</div>
                <div className="val eng">{viewModel.engagement}</div>
              </div>
              <div>
                <div className="lbl">Verifications</div>
                <div className="val">{verifications.length}</div>
              </div>
            </div>

            <div className="rate-card">
              <div className="lab">Estimated rate per post</div>
              <div className="v">{viewModel.rate}</div>
              <div className="note">Derived from follower band and campaign context.</div>
            </div>

            <div className="contact">
              {viewModel.links.map((link) => (
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
                <circle cx="65" cy="65" r="55" stroke="url(#matchG)" strokeWidth="10" fill="none" strokeDasharray="345.5" strokeDashoffset={`${345.5 - 3.455 * viewModel.matchScore}`} strokeLinecap="round"></circle>
              </svg>
              <div className="center">
                <div>
                  <div className="num">
                    {viewModel.matchScore}
                    <span className="pct">%</span>
                  </div>
                  <div className="label">AI Match</div>
                </div>
              </div>
            </div>
            <div>
              <h2>
                Canonical profile for{" "}
                <span className="accent">{campaign?.brand ?? viewModel.name}</span>.
              </h2>
              <p>
                Loaded from influencer, score, safety, and verification APIs
                {campaignId ? " with campaign context." : "."}
              </p>
              <div className="badge-row">
                <span className="mb good">Grade {viewModel.trustGrade}</span>
                <span className="mb">{viewModel.platform}</span>
                <span className="mb">{verifications.length} verifications</span>
                <span className="mb">{safetyFlags.length ? "Review flags" : "Brand safe"}</span>
              </div>
            </div>
          </section>

          <ScoreBreakdownPanel
            finalScore={campaignScore?.final_score as number | undefined}
            subScores={viewModel.subScores}
            positiveReasons={viewModel.positiveReasons}
            negativeReasons={viewModel.negativeReasons}
          />

          <SafetyFlagsPanel flags={safetyFlags} />

          <section className="panel">
            <div className="panel-head">
              <h3>
                <span className="pin"></span>Supporting Sources
              </h3>
              <span className="meta">{viewModel.citations.length} citations</span>
            </div>
            <div className="comments">
              {viewModel.citations.length ? (
                viewModel.citations.map((citation, index) => (
                  <div className="comment" key={citation}>
                    <div className={`cav c-av-${(index % 3) + 1}`} aria-hidden="true">
                      ↗
                    </div>
                    <div className="body">
                      <div className="who">{citationHost(citation)}</div>
                      <div className="txt source-link">
                        <a href={citation} target="_blank" rel="noopener noreferrer">
                          {citation}
                        </a>
                      </div>
                      <div className="txt muted-note">
                        Source used in campaign scoring provenance.
                      </div>
                    </div>
                    <span className="pill pill-neu">Source</span>
                  </div>
                ))
              ) : (
                <div className="comment">
                  <div className="cav c-av-1" aria-hidden="true">
                    —
                  </div>
                  <div className="body">
                    <div className="who">No citations recorded</div>
                    <div className="txt">
                      The backend did not return supporting source URLs for this profile.
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>

          <ProfileInteractions
            influencerId={influencerId}
            campaignId={campaignId}
            creatorName={viewModel.name}
            followerCount={viewModel.followerCount}
            deepAnalysis={
              campaignId ? (
                <DeepAnalysisTrigger
                  influencerId={influencerId}
                  campaignId={campaignId}
                  className="btn btn-ghost"
                  label="Run deep analysis"
                />
              ) : null
            }
          />
        </div>
      </div>
    </>
  );
}
