import React from 'react';
import Link from 'next/link';
import AppShell from '@/components/shell/AppShell';
import ProfileInteractions from '@/components/profile/ProfileInteractions';
import '../../profile.css';

export default function ProfilePage() {
  const crumbs = [
    { label: 'Workspace', href: '/' },
    { label: 'Discover', href: '/discover' },
    { label: 'Lila Park', current: true },
  ];

  return (
    <AppShell crumbs={crumbs}>
      <main className="content">
        <Link className="back-link" href="/discover">
          <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" style={{ width: '14px', height: '14px' }}>
            <path d="M15 6l-6 6 6 6" />
          </svg>
          Back to Discover
        </Link>

        <div className="layout">
          {/* ============= LEFT COLUMN ============= */}
          <div>
            <div className="panel">
              <div className="profile-head">
                <div className="pfp">
                  LP
                  <span className="verified" title="Verified creator">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
                      <circle cx="12" cy="12" r="9" />
                    </svg>
                  </span>
                </div>
                <div className="name-row">
                  <h1>Lila Park</h1>
                  <div className="handle">@lilaglow</div>
                  <div className="platforms" aria-label="Active on">
                    <a className="pf pf-ig" title="Instagram" href="#">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="3" y="3" width="18" height="18" rx="5" />
                        <circle cx="12" cy="12" r="4" />
                        <circle cx="17.5" cy="6.5" r="0.6" fill="currentColor" />
                      </svg>
                    </a>
                    <a className="pf pf-yt" title="YouTube" href="#">
                      <svg width="14" height="11" viewBox="0 0 24 18" fill="currentColor">
                        <path d="M23.5 3.5a3 3 0 0 0-2.1-2.1C19.5 1 12 1 12 1s-7.5 0-9.4.4A3 3 0 0 0 .5 3.5C.1 5.4.1 9 .1 9s0 3.6.4 5.5a3 3 0 0 0 2.1 2.1C4.5 17 12 17 12 17s7.5 0 9.4-.4a3 3 0 0 0 2.1-2.1c.4-1.9.4-5.5.4-5.5s0-3.6-.4-5.5zM9.5 12.5v-7L15.5 9l-6 3.5z" />
                      </svg>
                    </a>
                    <a className="pf pf-tt" title="TikTok" href="#">
                      <svg width="11" height="13" viewBox="0 0 20 22" fill="currentColor">
                        <path d="M14.5 1c.4 1.8 1.5 3.4 3 4.4 1.1.7 2.5 1.1 3.9 1.1V11c-1.6 0-3.2-.4-4.6-1.1-.6-.3-1.2-.7-1.7-1.1v6.6c0 4.1-3.4 7.5-7.5 7.5-1.6 0-3.1-.5-4.3-1.4-1.9-1.4-3.2-3.7-3.2-6.2 0-4.1 3.4-7.5 7.5-7.5.4 0 .9 0 1.3.1v4.4c-.4-.1-.8-.2-1.3-.2-1.7 0-3.1 1.4-3.1 3.1s1.4 3.2 3.2 3.2 3.2-1.4 3.2-3.1V1h3.6z" />
                      </svg>
                    </a>
                  </div>
                </div>
              </div>

              <p className="bio">
                Seoul-based skincare creator translating K-beauty rituals for a global audience. Best known for &quot;two-week glass-skin&quot; challenges, ingredient deep-dives, and morning routine reels. Posts thoughtfully —
                never more than two ads a month.
              </p>

              <div className="tags">
                <span className="tag violet">Beauty</span>
                <span className="tag">K-beauty</span>
                <span className="tag">Skincare</span>
                <span className="tag">Ingredient education</span>
                <span className="tag">Routines</span>
              </div>

              <div className="meta-row">
                <div className="item">
                  <span className="lab">Location</span>
                  <svg className="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                    <path d="M12 22s7-7 7-12a7 7 0 1 0-14 0c0 5 7 12 7 12z" />
                    <circle cx="12" cy="10" r="2.5" />
                  </svg>
                  <span>Seoul, South Korea</span>
                </div>
                <div className="item">
                  <span className="lab">Language</span>
                  <svg className="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                    <circle cx="12" cy="12" r="9" />
                    <path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" />
                  </svg>
                  <span>English, Korean</span>
                </div>
                <div className="item">
                  <span className="lab">Joined</span>
                  <svg className="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                    <rect x="3" y="5" width="18" height="16" rx="2" />
                    <path d="M3 9h18M8 3v4M16 3v4" />
                  </svg>
                  <span>March 2021</span>
                </div>
              </div>

              <div className="stats">
                <div>
                  <div className="lbl">Followers</div>
                  <div className="val">
                    341<span className="u">K</span>
                  </div>
                </div>
                <div>
                  <div className="lbl">Avg Views</div>
                  <div className="val">
                    82<span className="u">K</span>
                  </div>
                </div>
                <div>
                  <div className="lbl">Engagement</div>
                  <div className="val eng">
                    6.2<span className="u">%</span>
                  </div>
                </div>
                <div>
                  <div className="lbl">Posts / mo</div>
                  <div className="val">14</div>
                </div>
              </div>

              <div className="rate-card">
                <div className="lab">Estimated rate per post</div>
                <div className="v">
                  $1,800 <span className="from">– $2,600</span>
                </div>
                <div className="note">Based on category benchmarks · negotiable for multi-post campaigns</div>
              </div>

              <div className="contact">
                <div className="label">Contact</div>
                <a className="contact-item" href="#">
                  <span className="cico" style={{ background: 'linear-gradient(135deg,var(--violet),var(--coral))' }}>
                    <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                      <rect x="3" y="5" width="18" height="14" rx="2" />
                      <path d="m3 7 9 6 9-6" />
                    </svg>
                  </span>
                  <div className="cv">
                    <div className="k">Email</div>
                    <div className="val">lil****@gmail.com</div>
                  </div>
                  <span className="arr">→</span>
                </a>
                <a className="contact-item" href="#">
                  <span className="cico pf-ig">
                    <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                      <rect x="3" y="3" width="18" height="18" rx="5" />
                      <circle cx="12" cy="12" r="4" />
                      <circle cx="17.5" cy="6.5" r="0.6" fill="currentColor" />
                    </svg>
                  </span>
                  <div className="cv">
                    <div className="k">Instagram DM</div>
                    <div className="val">Send a message via @lilaglow</div>
                  </div>
                  <span className="arr">→</span>
                </a>
                <a className="contact-item" href="#">
                  <span className="cico" style={{ background: 'linear-gradient(135deg,var(--cyan),var(--violet))' }}>
                    <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                      <circle cx="12" cy="12" r="9" />
                      <path d="M3.5 9h17M3.5 15h17M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" />
                    </svg>
                  </span>
                  <div className="cv">
                    <div className="k">Website</div>
                    <div className="val">lilaglow.studio</div>
                  </div>
                  <span className="arr">→</span>
                </a>
              </div>
            </div>
          </div>

          {/* ============= RIGHT COLUMN ============= */}
          <div>
            {/* Match hero */}
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
                  <circle cx="65" cy="65" r="55" stroke="url(#matchG)" strokeWidth="10" fill="none" strokeDasharray="345.5" strokeDashoffset="27.6" strokeLinecap="round"></circle>
                </svg>
                <div className="center">
                  <div>
                    <div className="num">
                      92<span className="pct">%</span>
                    </div>
                    <div className="label">AI Match</div>
                  </div>
                </div>
              </div>
              <div>
                <h2>
                  An <span className="accent">excellent fit</span> for your brief.
                </h2>
                <p>
                  Lila ranks in the top 3% of beauty creators we&apos;ve assessed for &quot;skincare brand targeting women 20–35, $500 budget&quot; — strong demographic overlap, brand-safe content, and consistent posting cadence.
                </p>
                <div className="badge-row">
                  <span className="mb good">High audience fit</span>
                  <span className="mb">Brand safe</span>
                  <span className="mb">In budget</span>
                  <span className="mb">Consistent</span>
                </div>
              </div>
            </section>

            {/* Why we matched */}
            <section className="panel">
              <div className="panel-head">
                <h3>
                  <span className="pin"></span>Why We Matched You
                </h3>
                <span className="meta">Generated from your brief · 2 hours ago</span>
              </div>
              <div className="reasons">
                <div className="reason">
                  <span className="rico ri-1">
                    <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M16 11a4 4 0 1 0-8 0 4 4 0 0 0 8 0Z" />
                      <path d="M22 21a8 8 0 0 0-16 0" />
                    </svg>
                  </span>
                  <div className="body">
                    <div className="t">73% of this creator&apos;s audience matches your target demographic</div>
                    <div className="d">Women aged 20–35, predominantly in major North American and East Asian metros — strong overlap with your stated buyer profile.</div>
                  </div>
                </div>
                <div className="reason">
                  <span className="rico ri-2">
                    <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M3 12l4-4 4 6 4-8 6 10" />
                    </svg>
                  </span>
                  <div className="body">
                    <div className="t">High engagement on beauty and skincare content</div>
                    <div className="d">Average 6.2% engagement on the past 30 sponsored beauty posts — 2.4× the category benchmark.</div>
                  </div>
                </div>
                <div className="reason">
                  <span className="rico ri-3">
                    <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M12 1v22M5 8h11a3 3 0 0 1 0 6H8a3 3 0 0 0 0 6h12" />
                    </svg>
                  </span>
                  <div className="body">
                    <div className="t">Rate falls within your stated budget</div>
                    <div className="d">Estimated $1,800–$2,600 per post; comfortably within your $500–$3,000 range and open to bundle pricing.</div>
                  </div>
                </div>
                <div className="reason">
                  <span className="rico ri-4">
                    <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <rect x="3" y="5" width="18" height="16" rx="2" />
                      <path d="M3 9h18M8 3v4M16 3v4" />
                    </svg>
                  </span>
                  <div className="body">
                    <div className="t">Consistent posting — 3× per week average</div>
                    <div className="d">Reliable cadence across Instagram and TikTok. Your campaign will get steady-state visibility, not a single spike.</div>
                  </div>
                </div>
                <div className="reason">
                  <span className="rico ri-5">
                    <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M12 2 3 7v6c0 5 4 8 9 9 5-1 9-4 9-9V7l-9-5z" />
                      <path d="m9 12 2 2 4-4" />
                    </svg>
                  </span>
                  <div className="body">
                    <div className="t">Brand-safe — zero flagged content in past 24 months</div>
                    <div className="d">No controversies, hate-speech adjacency, or competing-brand exclusivity conflicts detected.</div>
                  </div>
                </div>
              </div>
            </section>

            {/* Audience: donut + bar / locations */}
            <div className="two-col">
              <section className="panel">
                <div className="panel-head">
                  <h3>
                    <span className="pin"></span>Audience Gender
                  </h3>
                </div>
                <div className="donut-wrap">
                  <div className="donut">
                    <svg width="120" height="120" viewBox="0 0 120 120">
                      <circle cx="60" cy="60" r="42" stroke="#f4f2ec" strokeWidth="14" fill="none" />
                      <circle cx="60" cy="60" r="42" stroke="oklch(0.74 0.18 30)" strokeWidth="14" fill="none" strokeDasharray="205.8 263.9" strokeDashoffset="0" strokeLinecap="butt" />
                      <circle cx="60" cy="60" r="42" stroke="oklch(0.58 0.22 285)" strokeWidth="14" fill="none" strokeDasharray="50.1 263.9" strokeDashoffset="-205.8" strokeLinecap="butt" />
                      <circle cx="60" cy="60" r="42" stroke="oklch(0.78 0.15 215)" strokeWidth="14" fill="none" strokeDasharray="7.9 263.9" strokeDashoffset="-255.9" strokeLinecap="butt" />
                    </svg>
                    <div className="ctr">
                      <div>
                        <div className="v">341K</div>
                        <div className="l">Audience</div>
                      </div>
                    </div>
                  </div>
                  <div className="legend">
                    <div className="row">
                      <span className="sw" style={{ background: 'oklch(0.74 0.18 30)' }}></span>
                      <span className="nm">Female</span>
                      <span className="pc">78%</span>
                    </div>
                    <div className="row">
                      <span className="sw" style={{ background: 'oklch(0.58 0.22 285)' }}></span>
                      <span className="nm">Male</span>
                      <span className="pc">19%</span>
                    </div>
                    <div className="row">
                      <span className="sw" style={{ background: 'oklch(0.78 0.15 215)' }}></span>
                      <span className="nm">Non-binary</span>
                      <span className="pc">3%</span>
                    </div>
                  </div>
                </div>
              </section>

              <section className="panel">
                <div className="panel-head">
                  <h3>
                    <span className="pin"></span>Audience Age
                  </h3>
                </div>
                <div className="bar-chart">
                  <div className="bar-row">
                    <span className="ag">18–24</span>
                    <span className="br">
                      <span style={{ width: '31%' }}></span>
                    </span>
                    <span className="pc">31%</span>
                  </div>
                  <div className="bar-row">
                    <span className="ag">25–34</span>
                    <span className="br">
                      <span style={{ width: '48%' }}></span>
                    </span>
                    <span className="pc">48%</span>
                  </div>
                  <div className="bar-row">
                    <span className="ag">35–44</span>
                    <span className="br">
                      <span style={{ width: '16%' }}></span>
                    </span>
                    <span className="pc">16%</span>
                  </div>
                  <div className="bar-row">
                    <span className="ag">45+</span>
                    <span className="br">
                      <span style={{ width: '5%' }}></span>
                    </span>
                    <span className="pc">5%</span>
                  </div>
                </div>
              </section>
            </div>

            {/* Top locations + Sentiment */}
            <section className="panel">
              <div className="panel-head">
                <h3>
                  <span className="pin"></span>Top Audience Locations
                </h3>
                <span className="meta">Last 90 days</span>
              </div>
              <div className="loc-list">
                <div className="loc">
                  <span className="rk">1</span>
                  <span className="nm">United States</span>
                  <span className="br">
                    <span style={{ width: '100%' }}></span>
                  </span>
                  <span className="pc">34%</span>
                </div>
                <div className="loc">
                  <span className="rk">2</span>
                  <span className="nm">South Korea</span>
                  <span className="br">
                    <span style={{ width: '65%' }}></span>
                  </span>
                  <span className="pc">22%</span>
                </div>
                <div className="loc">
                  <span className="rk">3</span>
                  <span className="nm">Canada</span>
                  <span className="br">
                    <span style={{ width: '38%' }}></span>
                  </span>
                  <span className="pc">13%</span>
                </div>
                <div className="loc">
                  <span className="rk">4</span>
                  <span className="nm">United Kingdom</span>
                  <span className="br">
                    <span style={{ width: '26%' }}></span>
                  </span>
                  <span className="pc">9%</span>
                </div>
                <div className="loc">
                  <span className="rk">5</span>
                  <span className="nm">Australia</span>
                  <span className="br">
                    <span style={{ width: '18%' }}></span>
                  </span>
                  <span className="pc">6%</span>
                </div>
              </div>
            </section>

            {/* Sentiment */}
            <section className="panel">
              <div className="panel-head">
                <h3>
                  <span className="pin"></span>Comment Sentiment
                </h3>
                <span className="meta">Last 500 comments</span>
              </div>
              <div className="sent-bar">
                <span className="sent-pos" style={{ width: '84%' }}></span>
                <span className="sent-neu" style={{ width: '13%' }}></span>
                <span className="sent-neg" style={{ width: '3%' }}></span>
              </div>
              <div className="sent-legend">
                <div className="row">
                  <span className="sw" style={{ background: 'var(--good)' }}></span>Positive <span className="pc">84%</span>
                </div>
                <div className="row">
                  <span className="sw" style={{ background: 'oklch(0.78 0.06 80)' }}></span>Neutral <span className="pc">13%</span>
                </div>
                <div className="row">
                  <span className="sw" style={{ background: 'var(--coral)' }}></span>Negative <span className="pc">3%</span>
                </div>
              </div>

              <div className="comments">
                <div className="comment">
                  <span className="cav c-av-1">SK</span>
                  <div>
                    <div className="who">@skincare_diaries · 2d</div>
                    <div className="txt">&quot;This is the only routine that&apos;s actually worked on my texture issues. The way you explain ingredients without the fear-mongering is so refreshing.&quot;</div>
                  </div>
                  <span className="pill pill-pos">Positive</span>
                </div>
                <div className="comment">
                  <span className="cav c-av-2">JM</span>
                  <div>
                    <div className="who">@jenmoss · 4d</div>
                    <div className="txt">&quot;Loved the niacinamide breakdown. Could you do a follow-up on retinol layering? I&apos;m always nervous about combining actives.&quot;</div>
                  </div>
                  <span className="pill pill-pos">Positive</span>
                </div>
                <div className="comment">
                  <span className="cav c-av-3">RT</span>
                  <div>
                    <div className="who">@rae.t · 5d</div>
                    <div className="txt">&quot;Curious about the SPF you reused — was that an older PR sample or current formulation?&quot;</div>
                  </div>
                  <span className="pill pill-neu">Neutral</span>
                </div>
              </div>
            </section>

            <ProfileInteractions />
          </div>
        </div>
      </main>
    </AppShell>
  );
}
