'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createCampaign, getOnboarding } from '@/lib/api';
import { briefDefaultsFromBrandProfile } from '@/lib/brandProfile';
import { buildBriefSnapshot } from '@/lib/campaignPayload';
import { useToast } from '@/components/ui/ToastProvider';

export default function BriefForm() {
  const router = useRouter();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(-1);
  const [profileCount, setProfileCount] = useState(0);

  const [brief, setBrief] = useState({
    brand: '',
    product: '',
    category: 'Outdoor & Activewear',
    campaign: '',
    goal: '',
    ages: [] as string[],
    gender: 'All',
    lang: 'English',
    locs: [] as string[],
    interests: [] as string[],
    budgetMin: 2500,
    budgetMax: 12000,
    currency: 'USD',
    platforms: [] as string[],
    tier: 'Established',
    notes: ''
  });

  useEffect(() => {
    let cancelled = false;
    getOnboarding()
      .then((profile) => {
        if (cancelled) return;
        const defaults = briefDefaultsFromBrandProfile(profile);
        setBrief((prev) => ({
          ...prev,
          brand: defaults.brand || prev.brand,
          category: defaults.category || prev.category,
          goal: defaults.goal || prev.goal,
          platforms: defaults.platforms.length ? defaults.platforms : prev.platforms,
          budgetMax: defaults.budgetMax,
          budgetMin: Math.min(prev.budgetMin, defaults.budgetMax),
          locs: profile.country && profile.country !== 'Global' ? [profile.country] : prev.locs,
        }));
      })
      .catch(() => {
        // User hasn't onboarded — keep form defaults.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const [tagInput, setTagInput] = useState('');

  // Handle chips
  const toggleChip = (group: 'ages' | 'locs', val: string) => {
    setBrief(prev => ({
      ...prev,
      [group]: prev[group].includes(val)
        ? prev[group].filter(v => v !== val)
        : [...prev[group], val]
    }));
  };

  // Handle segmented
  const setSegmented = (key: 'gender' | 'currency', val: string) => {
    setBrief(prev => ({ ...prev, [key]: val }));
  };

  // Handle tags
  const addTag = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && tagInput.trim()) {
      e.preventDefault();
      if (!brief.interests.includes(tagInput.trim())) {
        setBrief(prev => ({ ...prev, interests: [...prev.interests, tagInput.trim()] }));
      }
      setTagInput('');
    }
  };
  const removeTag = (tag: string) => {
    setBrief(prev => ({ ...prev, interests: prev.interests.filter(t => t !== tag) }));
  };

  // Handle budget
  const handleRange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = parseInt(e.target.value);
    setBrief(prev => ({ ...prev, budgetMax: v }));
  };
  const handleMin = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = parseInt(e.target.value.replace(/[^0-9]/g, '')) || 500;
    setBrief(prev => ({ ...prev, budgetMin: v }));
  };

  const syncRangeStyles = () => {
    const min = 500, max = 50000;
    const p1 = ((brief.budgetMin - min) / (max - min)) * 100;
    const p2 = ((brief.budgetMax - min) / (max - min)) * 100;
    return { '--p1': `${p1}%`, '--p2': `${p2}%` } as React.CSSProperties;
  };

  const getBudgetText = () => {
    const sym = brief.currency === 'BDT' ? '৳' : '$';
    return `${sym}${brief.budgetMin.toLocaleString()} – ${sym}${brief.budgetMax.toLocaleString()} ${brief.currency}`;
  };

  // Handle platforms
  const togglePlatform = (p: string) => {
    setBrief(prev => ({
      ...prev,
      platforms: prev.platforms.includes(p)
        ? prev.platforms.filter(x => x !== p)
        : [...prev.platforms, p]
    }));
  };

  // Submit flow
  const handleFindMatches = async () => {
    if (loading) {
      return;
    }

    setLoading(true);
    setLoadingStep(-1);
    setProfileCount(0);
    let step = 0;
    let n = 0;

    const counterInterval = setInterval(() => {
      n += 1247;
      setProfileCount(Math.min(50247, n));
    }, 60);

    const stepTimer = window.setInterval(() => {
      setLoadingStep(current => {
        if (current >= 3) {
          window.clearInterval(stepTimer);
          return current;
        }
        step += 1;
        return step - 1;
      });
    }, 700);

    try {
      const [campaign] = await Promise.all([
        createCampaign(
          {
            brand: brief.brand,
            product: brief.product,
            category: brief.category,
            goal: brief.goal,
            ages: brief.ages,
            gender: brief.gender,
            locations: brief.locs,
            platforms: brief.platforms.map(platform => platform.toLowerCase()),
            tier: brief.tier,
            budget: getBudgetText(),
            notes: brief.notes,
          },
          {
            entryPoint: 'brief_form',
            campaignName: brief.campaign || brief.product,
            briefSnapshot: buildBriefSnapshot(brief),
          }
        ),
        new Promise(resolve => window.setTimeout(resolve, 1800)),
      ]);

      clearInterval(counterInterval);
      window.clearInterval(stepTimer);
      setProfileCount(50247);
      setLoadingStep(3);

      window.setTimeout(() => {
        router.push(`/shortlist?campaignId=${encodeURIComponent(campaign.campaignId)}`);
      }, 450);
    } catch (error) {
      clearInterval(counterInterval);
      window.clearInterval(stepTimer);
      setLoading(false);
      setLoadingStep(-1);
      setProfileCount(0);
      toast(
        error instanceof Error ? error.message : 'Unable to submit campaign right now.',
        { type: 'error' }
      );
    }
  };

  return (
    <>
      <div className="form-wrap">
        {/* ===== FORM ===== */}
        <form className="form-card" onSubmit={(e) => e.preventDefault()}>
          {/* Brand */}
          <section className="section">
            <div className="section-head"><span className="num">1</span><h2>Brand & product</h2><span className="desc">The basics about what you&apos;re promoting.</span></div>
            <div className="grid-2">
              <div className="field">
                <label>Brand Name <span className="req">*</span></label>
                <input className="input" placeholder="e.g. Northwind Outdoor" value={brief.brand} onChange={e => setBrief({...brief, brand: e.target.value})} />
              </div>
              <div className="field">
                <label>Product / Service Name <span className="req">*</span></label>
                <input className="input" placeholder="e.g. SS26 Trail Capsule" value={brief.product} onChange={e => setBrief({...brief, product: e.target.value})} />
              </div>
              <div className="field">
                <label>Product Category <span className="req">*</span></label>
                <div className="select-wrap">
                  <select className="select" value={brief.category} onChange={e => setBrief({...brief, category: e.target.value})}>
                    <option>Fashion & Apparel</option>
                    <option>Outdoor & Activewear</option>
                    <option>Beauty & Skincare</option>
                    <option>Food & Beverage</option>
                    <option>Tech & Gadgets</option>
                    <option>Health & Wellness</option>
                    <option>Travel & Hospitality</option>
                    <option>Home & Lifestyle</option>
                    <option>Gaming & Entertainment</option>
                    <option>Finance & Fintech</option>
                  </select>
                </div>
              </div>
              <div className="field">
                <label>Campaign Name <span className="hint">(internal)</span></label>
                <input className="input" placeholder="e.g. SS26 trail launch — May" value={brief.campaign} onChange={e => setBrief({...brief, campaign: e.target.value})} />
              </div>
            </div>
          </section>

          {/* Goal */}
          <section className="section">
            <div className="section-head"><span className="num">2</span><h2>Campaign goal</h2><span className="desc">Pick the primary outcome.</span></div>
            <div className="goal-grid">
              {[
                { id: 'Brand Awareness', icon: <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.7"><circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="7" opacity="0.6"/><circle cx="12" cy="12" r="11" opacity="0.3"/></svg>, desc: 'Maximize reach & impressions', class: 'goal-1' },
                { id: 'Product Launch', icon: <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M4 13l8-9 8 9-8 7-8-7z"/><path d="M9 16l3-3 3 3"/></svg>, desc: 'Drive buzz on a new drop', class: 'goal-2' },
                { id: 'Sales Conversion', icon: <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M3 17l5-5 4 4 8-8"/><path d="M16 8h4v4"/></svg>, desc: 'Track clicks & purchases', class: 'goal-3' },
                { id: 'Event Promotion', icon: <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.7"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 9h18M8 3v4M16 3v4"/></svg>, desc: 'Fill seats & RSVPs', class: 'goal-4' },
              ].map(g => (
                <label key={g.id} className={`goal ${g.class}`}>
                  <input type="radio" name="goal" value={g.id} checked={brief.goal === g.id} onChange={e => setBrief({...brief, goal: e.target.value})} />
                  <span className="ico">{g.icon}</span>
                  <div className="t">{g.id}</div>
                  <div className="d">{g.desc}</div>
                </label>
              ))}
            </div>
          </section>

          {/* Audience */}
          <section className="section">
            <div className="section-head"><span className="num">3</span><h2>Target audience</h2><span className="desc">Who you want to reach.</span></div>

            <div className="field" style={{ marginBottom: '18px' }}>
              <label>Age Range <span className="hint">(select all that apply)</span></label>
              <div className="chips">
                {['13–17', '18–24', '25–34', '35–44', '45–54', '55+'].map(age => (
                  <span key={age} className={`chip ${brief.ages.includes(age) ? 'on' : ''}`} onClick={() => toggleChip('ages', age)}>{age}</span>
                ))}
              </div>
            </div>

            <div className="grid-2" style={{ marginBottom: '18px' }}>
              <div className="field">
                <label>Gender</label>
                <div className="seg">
                  {['All', 'Female', 'Male', 'Other'].map(g => (
                    <button key={g} type="button" className={brief.gender === g ? 'on' : ''} onClick={() => setSegmented('gender', g)}>{g}</button>
                  ))}
                </div>
              </div>
              <div className="field">
                <label>Primary Language</label>
                <div className="select-wrap">
                  <select className="select" value={brief.lang} onChange={e => setBrief({...brief, lang: e.target.value})}>
                    <option>English</option>
                    <option>Bengali</option>
                    <option>Hindi</option>
                    <option>Spanish</option>
                    <option>French</option>
                    <option>German</option>
                    <option>Japanese</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="field" style={{ marginBottom: '18px' }}>
              <label>Audience Location <span className="hint">(multi-select)</span></label>
              <div className="chips">
                {[
                  { id: 'USA', flag: '🇺🇸' },
                  { id: 'Canada', flag: '🇨🇦' },
                  { id: 'UK', flag: '🇬🇧' },
                  { id: 'India', flag: '🇮🇳' },
                  { id: 'Bangladesh', flag: '🇧🇩' },
                  { id: 'Australia', flag: '🇦🇺' },
                  { id: 'Germany', flag: '🇩🇪' },
                  { id: 'Global', flag: '🌍' }
                ].map(loc => (
                  <span key={loc.id} className={`chip ${brief.locs.includes(loc.id) ? 'on' : ''}`} onClick={() => toggleChip('locs', loc.id)}>{loc.flag} {loc.id}</span>
                ))}
              </div>
            </div>

            <div className="field">
              <label>Audience Interests <span className="hint">(press Enter to add)</span></label>
              <div className="tag-input">
                {brief.interests.map(tag => (
                  <span key={tag} className="tag-pill">{tag}<button type="button" onClick={() => removeTag(tag)}>×</button></span>
                ))}
                <input placeholder="Add interest…" value={tagInput} onChange={e => setTagInput(e.target.value)} onKeyDown={addTag} />
              </div>
            </div>
          </section>

          {/* Budget */}
          <section className="section">
            <div className="section-head"><span className="num">4</span><h2>Budget</h2><span className="desc">Total spend across creators.</span></div>
            <div className="budget-row">
              <div className="field">
                <label>Min</label>
                <input className="input mono" type="text" value={`$${brief.budgetMin.toLocaleString()}`} onChange={handleMin} />
              </div>
              <div className="field">
                <label>Range</label>
                <div className="range-wrap">
                  <input type="range" className="range" min="500" max="50000" step="500" value={brief.budgetMax} onChange={handleRange} style={syncRangeStyles()} />
                  <div className="budget-readout"><span>$500</span><strong>{getBudgetText()}</strong><span>$50,000</span></div>
                </div>
              </div>
              <div className="field">
                <label>Max</label>
                <input className="input mono" type="text" value={`$${brief.budgetMax.toLocaleString()}`} readOnly />
              </div>
            </div>
            <div className="currency-row">
              <span className="lbl">Currency</span>
              <div className="seg">
                <button type="button" className={brief.currency === 'USD' ? 'on' : ''} onClick={() => setSegmented('currency', 'USD')}>USD $</button>
                <button type="button" className={brief.currency === 'BDT' ? 'on' : ''} onClick={() => setSegmented('currency', 'BDT')}>BDT ৳</button>
              </div>
            </div>
          </section>

          {/* Platforms */}
          <section className="section">
            <div className="section-head"><span className="num">5</span><h2>Preferred platforms</h2><span className="desc">Pick one or more.</span></div>
            <div className="pf-grid">
              {[
                { id: 'Instagram', meta: '1.2M creators', class: 'pf-ig', icon: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="0.5" fill="white"/></svg> },
                { id: 'YouTube', meta: '680K creators', class: 'pf-yt', icon: <svg width="14" height="11" viewBox="0 0 24 18" fill="white"><path d="M23.5 3.5a3 3 0 0 0-2.1-2.1C19.5 1 12 1 12 1s-7.5 0-9.4.4A3 3 0 0 0 .5 3.5C.1 5.4.1 9 .1 9s0 3.6.4 5.5a3 3 0 0 0 2.1 2.1C4.5 17 12 17 12 17s7.5 0 9.4-.4a3 3 0 0 0 2.1-2.1c.4-1.9.4-5.5.4-5.5s0-3.6-.4-5.5zM9.5 12.5v-7L15.5 9l-6 3.5z"/></svg> },
                { id: 'TikTok', meta: '412K creators', class: 'pf-tt', icon: <svg width="12" height="13" viewBox="0 0 20 22" fill="white"><path d="M14.5 1c.4 1.8 1.5 3.4 3 4.4 1.1.7 2.5 1.1 3.9 1.1V11c-1.6 0-3.2-.4-4.6-1.1-.6-.3-1.2-.7-1.7-1.1v6.6c0 4.1-3.4 7.5-7.5 7.5-1.6 0-3.1-.5-4.3-1.4-1.9-1.4-3.2-3.7-3.2-6.2 0-4.1 3.4-7.5 7.5-7.5.4 0 .9 0 1.3.1v4.4c-.4-.1-.8-.2-1.3-.2-1.7 0-3.1 1.4-3.1 3.1s1.4 3.2 3.2 3.2 3.2-1.4 3.2-3.1V1h3.6z"/></svg> },
                { id: 'Facebook', meta: '156K creators', class: 'pf-fb', icon: <svg width="11" height="11" viewBox="0 0 24 24" fill="white"><path d="M14 9V7c0-1 .5-2 2-2h2V1h-3c-3 0-5 2-5 5v3H7v4h3v9h4v-9h3l1-4h-4z"/></svg> },
              ].map(p => (
                <label key={p.id} className="pf-tile">
                  <input type="checkbox" checked={brief.platforms.includes(p.id)} onChange={() => togglePlatform(p.id)} />
                  <span className={`glyph ${p.class}`}>{p.icon}</span>
                  <div><div className="nm">{p.id}</div><div className="meta">{p.meta}</div></div>
                  <span className="check"><svg viewBox="0 0 16 12" width="10" height="8"><path d="M1 6 L6 11 L15 1" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" fill="none"/></svg></span>
                </label>
              ))}
            </div>
          </section>

          {/* Tier */}
          <section className="section">
            <div className="section-head"><span className="num">6</span><h2>Influencer tier</h2><span className="desc">Where you&apos;d like us to focus.</span></div>
            <div className="tier-grid">
              {[
                { id: 'Rising', range: '< 50K', style: { background: 'var(--cyan-soft)', color: 'var(--cyan-ink)' }, desc: 'Emerging voices, high engagement, low cost per post.' },
                { id: 'Established', range: '50K – 500K', style: { background: 'var(--amber-soft)', color: 'var(--amber-ink)' }, desc: 'Reliable mid-tier reach, balanced ER & rate.' },
                { id: 'Premium', range: '500K+', style: { background: 'var(--violet-soft)', color: 'var(--violet-ink)' }, desc: 'Top-tier creators with major mainstream reach.' },
                { id: 'No Preference', range: 'Auto', style: { background: 'var(--paper-2)', color: 'var(--muted)' }, desc: 'Let the AI pick the right mix per goal.' },
              ].map(t => (
                <label key={t.id} className="tier">
                  <input type="radio" name="tier" checked={brief.tier === t.id} onChange={() => setBrief({...brief, tier: t.id})} />
                  <div className="name">{t.id}</div>
                  <span className="range-lab" style={t.style}>{t.range}</span>
                  <div className="desc">{t.desc}</div>
                </label>
              ))}
            </div>
          </section>

          {/* Notes */}
          <section className="section">
            <div className="section-head"><span className="num">7</span><h2>Additional notes</h2><span className="desc">Anything else our matching model should weigh.</span></div>
            <div className="field">
              <label>Notes for the matching engine</label>
              <textarea className="textarea" placeholder="e.g. Prefer creators who hike or trail run. Avoid heavy fashion-vlog content. Pacific Northwest a strong plus." value={brief.notes} onChange={e => setBrief({...brief, notes: e.target.value})} />
            </div>
          </section>

          {/* Footer */}
          <div className="form-foot">
            <div className="meta"><span className="dot"></span>Brief auto-saves as you type</div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button type="button" className="btn btn-ghost">Save draft</button>
              <button type="button" className="btn btn-primary btn-lg" onClick={handleFindMatches}>
                <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 3l1.8 4.5L18 9.3l-4.2 1.8L12 15.6l-1.8-4.5L6 9.3l4.2-1.8L12 3z"/></svg>
                Find My Matches
                <span className="arrow">→</span>
              </button>
            </div>
          </div>
        </form>

        {/* ===== Preview sidebar ===== */}
        <aside className="preview">
          <h4>Brief preview</h4>
          <div className="row"><span className="k">Brand</span><span className="v">{brief.brand || '—'}</span></div>
          <div className="row"><span className="k">Product</span><span className="v">{brief.product || '—'}</span></div>
          <div className="row"><span className="k">Category</span><span className="v">{brief.category || '—'}</span></div>
          <div className="row"><span className="k">Goal</span><span className="v">{brief.goal || '—'}</span></div>
          <div className="row"><span className="k">Ages</span><span className="v stack">
            {brief.ages.length ? brief.ages.map(a => <span key={a} className="pill">{a}</span>) : <span style={{ color: 'var(--muted-soft)', fontStyle: 'italic' }}>none</span>}
          </span></div>
          <div className="row"><span className="k">Gender</span><span className="v">{brief.gender}</span></div>
          <div className="row"><span className="k">Locations</span><span className="v stack">
            {brief.locs.length ? brief.locs.map(l => <span key={l} className="pill">{l}</span>) : <span style={{ color: 'var(--muted-soft)', fontStyle: 'italic' }}>none</span>}
          </span></div>
          <div className="row"><span className="k">Platforms</span><span className="v stack">
            {brief.platforms.length ? brief.platforms.map(p => <span key={p} className="pill">{p}</span>) : <span style={{ color: 'var(--muted-soft)', fontStyle: 'italic' }}>none</span>}
          </span></div>
          <div className="row"><span className="k">Tier</span><span className="v">{brief.tier}</span></div>
          <div className="row">
            <span className="k">Budget</span>
            <span className="v">
              {getBudgetText().includes('USD') ? (
                <>
                  {getBudgetText().replace(' USD', '')}
                  <br />
                  <span style={{ fontSize: '11px', color: 'var(--muted)' }}>USD</span>
                </>
              ) : getBudgetText().includes('BDT') ? (
                <>
                  {getBudgetText().replace(' BDT', '')}
                  <br />
                  <span style={{ fontSize: '11px', color: 'var(--muted)' }}>BDT</span>
                </>
              ) : getBudgetText()}
            </span>
          </div>
        </aside>
      </div>

      {/* ===== Loading overlay ===== */}
      <div className={`loading ${loading ? 'on' : ''}`} role="dialog" aria-live="polite">
        <div className="loading-card">
          <div className="loading-orb"></div>
          <h3>InfluenceIQ AI is analyzing<br/><span style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontStyle: 'italic', background: 'linear-gradient(120deg,var(--violet),var(--coral))', WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent' }}>50,000+ influencer profiles…</span></h3>
          <p>Reading your brief and ranking creators on <span className="count">{profileCount.toLocaleString()}</span> dimensions.</p>
          <div className="loading-steps">
            {[
              'Parsing brief & extracting intent',
              'Querying 50,247 vetted creator profiles',
              'Scoring audience & content fit',
              'Ranking your top matches'
            ].map((step, idx) => (
              <div key={idx} className={`loading-step ${loadingStep > idx ? 'done' : loadingStep === idx ? 'active' : ''}`}>
                <span className="tick">
                  {loadingStep > idx ? (
                    <svg viewBox="0 0 16 12" width="9" height="7"><path d="M1 6 L6 11 L15 1" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" fill="none"/></svg>
                  ) : null}
                </span>
                {step}
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
