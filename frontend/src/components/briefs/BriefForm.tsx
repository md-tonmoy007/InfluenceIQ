'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  createCampaign,
  createCampaignDraft,
  getCampaign,
  getOnboarding,
  submitCampaign,
  updateCampaignDraft,
} from '@/lib/api';
import { briefDefaultsFromBrandProfile } from '@/lib/brandProfile';
import {
  buildBriefSnapshot,
  briefFormFromSnapshot,
  type BriefFormPayload,
} from '@/lib/campaignPayload';
import { useToast } from '@/components/ui/ToastProvider';
import { WeightSliders } from '@/components/briefs/WeightSliders';
import CampaignBriefActions from '@/components/campaigns/CampaignBriefActions';
import { canEditCampaignBrief } from '@/lib/campaignLifecycle';
import { DEFAULT_CAMPAIGN_WEIGHTS, type CampaignBriefPayload, type CampaignWeights } from '@/types/campaign';

type FieldErrors = Partial<Record<'brand' | 'description' | 'platforms', string>>;

const emptyBrief = (): BriefFormPayload => ({
  brand: '',
  description: '',
  campaign: '',
  locs: [],
  budgetMin: 2500,
  budgetMax: 12000,
  currency: 'USD',
  platforms: [],
  tier: 'Established',
});

export default function BriefForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const draftCampaignId = searchParams.get('campaignId') || '';
  const fromCampaignId = searchParams.get('from') || '';
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [hydrating, setHydrating] = useState(Boolean(draftCampaignId || fromCampaignId));
  const [loadingStep, setLoadingStep] = useState(-1);
  const [profileCount, setProfileCount] = useState(0);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [activeDraftId, setActiveDraftId] = useState(draftCampaignId);
  const [activeCampaignStatus, setActiveCampaignStatus] = useState('draft');
  const [activeCampaignLabel, setActiveCampaignLabel] = useState('');

  const [brief, setBrief] = useState<BriefFormPayload>(emptyBrief);
  const [weights, setWeights] = useState<CampaignWeights>(DEFAULT_CAMPAIGN_WEIGHTS);
  const canSubmitBrief = canEditCampaignBrief(activeCampaignStatus);

  useEffect(() => {
    let cancelled = false;
    const loadId = draftCampaignId || fromCampaignId;
    if (loadId) {
      setHydrating(true);
      getCampaign(loadId)
        .then((campaign) => {
          if (cancelled) return;
          const hydrated = briefFormFromSnapshot(campaign.briefSnapshot, {
            searchQuery: campaign.searchQuery,
            product: campaign.product,
            budget_range: campaign.budgetRange,
            campaign_name: campaign.campaignName,
          });
          setBrief(hydrated);
          setActiveCampaignStatus(campaign.status);
          setActiveCampaignLabel(
            campaign.campaignName || campaign.searchQuery || campaign.product || 'Untitled campaign'
          );
          if (draftCampaignId) {
            setActiveDraftId(draftCampaignId);
          }
        })
        .catch((error) => {
          if (!cancelled) {
            toast(
              error instanceof Error ? error.message : 'Unable to load campaign brief.',
              { type: 'error' }
            );
          }
        })
        .finally(() => {
          if (!cancelled) setHydrating(false);
        });
      return () => {
        cancelled = true;
      };
    }

    getOnboarding()
      .then((profile) => {
        if (cancelled) return;
        const defaults = briefDefaultsFromBrandProfile(profile);
        setBrief((prev) => ({
          ...prev,
          brand: defaults.brand || prev.brand,
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
  }, [draftCampaignId, fromCampaignId, toast]);

  // Handle chips
  const toggleLocation = (val: string) => {
    setBrief(prev => ({
      ...prev,
      locs: prev.locs.includes(val)
        ? prev.locs.filter(v => v !== val)
        : [...prev.locs, val]
    }));
  };

  const setCurrency = (val: string) => {
    setBrief(prev => ({ ...prev, currency: val }));
  };

  // Handle budget
  const budgetFloor = 500;
  const budgetCeiling = 50000;
  const budgetSymbol = brief.currency === 'BDT' ? '৳' : '$';
  const budgetMinPct =
    ((brief.budgetMin - budgetFloor) / (budgetCeiling - budgetFloor)) * 100;
  const budgetMaxPct =
    ((brief.budgetMax - budgetFloor) / (budgetCeiling - budgetFloor)) * 100;

  const handleRange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = parseInt(e.target.value, 10);
    setBrief(prev => ({ ...prev, budgetMax: Math.max(v, prev.budgetMin) }));
  };
  const handleMin = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = parseInt(e.target.value.replace(/[^0-9]/g, ''), 10) || budgetFloor;
    setBrief(prev => ({ ...prev, budgetMin: Math.min(Math.max(v, budgetFloor), prev.budgetMax) }));
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

  const briefPayload = (): CampaignBriefPayload => ({
    brand: brief.brand,
    description: brief.description,
    locations: brief.locs,
    platforms: brief.platforms.map((platform) => platform.toLowerCase()),
    tier: brief.tier,
    budget: getBudgetText(),
    notes: brief.description,
  });

  const draftUpdateBody = () => ({
    search_query: brief.description,
    preferred_platforms: brief.platforms.length
      ? brief.platforms.map((platform) => platform.toLowerCase())
      : null,
    budget_range: getBudgetText(),
    campaign_name: brief.campaign || brief.description.slice(0, 120),
    brief_snapshot: buildBriefSnapshot(brief),
  });

  const validateBrief = (): boolean => {
    const errors: FieldErrors = {};
    if (!brief.brand.trim()) errors.brand = 'Brand name is required.';
    if (!brief.description.trim()) errors.description = 'Describe your campaign.';
    if (!brief.platforms.length) errors.platforms = 'Select at least one platform.';
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const friendlyError = (error: unknown) => {
    if (error instanceof Error && error.message.includes('409')) {
      return 'A conflicting campaign already exists. Try again or use a different Idempotency-Key.';
    }
    return error instanceof Error ? error.message : 'Unable to save campaign right now.';
  };

  const handleSaveDraft = async () => {
    if (savingDraft || loading) return;
    if (!brief.brand.trim() || !brief.description.trim()) {
      setFieldErrors({
        brand: !brief.brand.trim() ? 'Brand name is required.' : undefined,
        description: !brief.description.trim() ? 'Describe your campaign.' : undefined,
      });
      toast('Brand and campaign description are required to save a draft.', { type: 'error' });
      return;
    }

    setSavingDraft(true);
    try {
      if (activeDraftId) {
        await updateCampaignDraft(activeDraftId, draftUpdateBody());
        toast('Draft saved.', { type: 'success' });
      } else {
        const created = await createCampaignDraft(briefPayload(), {
          entryPoint: 'brief_form',
          campaignName: brief.campaign || brief.description.slice(0, 120),
          searchQuery: brief.description,
          briefSnapshot: buildBriefSnapshot(brief),
        });
        setActiveDraftId(created.campaignId);
        router.replace(`/briefs/new?campaignId=${encodeURIComponent(created.campaignId)}`);
        toast('Draft saved.', { type: 'success' });
      }
    } catch (error) {
      toast(friendlyError(error), { type: 'error' });
    } finally {
      setSavingDraft(false);
    }
  };

  // Submit flow
  const handleFindMatches = async () => {
    if (loading || !validateBrief()) {
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
      const runSubmit = async () => {
        if (activeDraftId) {
          await updateCampaignDraft(activeDraftId, draftUpdateBody());
          return submitCampaign(activeDraftId);
        }
        return createCampaign(briefPayload(), {
          entryPoint: 'brief_form',
          campaignName: brief.campaign || brief.description.slice(0, 120),
          searchQuery: brief.description,
          briefSnapshot: buildBriefSnapshot(brief),
          weights,
        });
      };

      const [campaign] = await Promise.all([
        runSubmit(),
        new Promise((resolve) => window.setTimeout(resolve, 1800)),
      ]);

      clearInterval(counterInterval);
      window.clearInterval(stepTimer);
      setProfileCount(50247);
      setLoadingStep(3);

      window.setTimeout(() => {
        router.push(`/matching?campaignId=${encodeURIComponent(campaign.campaignId)}`);
      }, 450);
    } catch (error) {
      clearInterval(counterInterval);
      window.clearInterval(stepTimer);
      setLoading(false);
      setLoadingStep(-1);
      setProfileCount(0);
      toast(
        friendlyError(error),
        { type: 'error' }
      );
    }
  };

  if (hydrating) {
    return (
      <div className="form-wrap">
        <div className="form-card" style={{ opacity: 0.7 }}>
          Loading campaign brief…
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="form-wrap">
        {/* ===== FORM ===== */}
        <form className="form-card" onSubmit={(e) => e.preventDefault()}>
          {/* Brand */}
          <section className="section">
            <div className="section-head"><span className="num">1</span><h2>Brand & campaign</h2><span className="desc">The basics about what you&apos;re promoting.</span></div>
            <div className="grid-2">
              <div className="field">
                <label>Brand Name <span className="req">*</span></label>
                <input className="input" placeholder="e.g. Northwind Outdoor" value={brief.brand} onChange={e => setBrief({...brief, brand: e.target.value})} />
                {fieldErrors.brand ? <span className="hint" style={{ color: 'var(--coral)' }}>{fieldErrors.brand}</span> : null}
              </div>
              <div className="field">
                <label>Campaign Name <span className="hint">(internal)</span></label>
                <input className="input" placeholder="e.g. SS26 trail launch — May" value={brief.campaign} onChange={e => setBrief({...brief, campaign: e.target.value})} />
              </div>
            </div>
            <div className="field">
              <label>Describe your campaign <span className="req">*</span></label>
              <textarea
                className="textarea"
                placeholder="e.g. SS26 Trail Capsule, an outdoor & activewear product launch. Looking for hiking and trail-running creators to drive awareness."
                value={brief.description}
                onChange={e => setBrief({...brief, description: e.target.value})}
              />
              {fieldErrors.description ? <span className="hint" style={{ color: 'var(--coral)' }}>{fieldErrors.description}</span> : null}
            </div>
          </section>

          <section className="section">
            <div className="section-head"><span className="num">2</span><h2>Target locations</h2><span className="desc">Where your audience is.</span></div>

            <div className="field">
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
                  <span key={loc.id} className={`chip ${brief.locs.includes(loc.id) ? 'on' : ''}`} onClick={() => toggleLocation(loc.id)}>{loc.flag} {loc.id}</span>
                ))}
              </div>
            </div>
          </section>

          {/* Budget */}
          <section className="section">
            <div className="section-head"><span className="num">3</span><h2>Budget</h2><span className="desc">Total spend across creators.</span></div>
            <div className="budget-row">
              <div className="field budget-field-min">
                <label>Min</label>
                <input
                  className="input mono"
                  type="text"
                  value={`${budgetSymbol}${brief.budgetMin.toLocaleString()}`}
                  onChange={handleMin}
                />
              </div>
              <div className="field budget-field-range">
                <label>Range</label>
                <div className="budget-slider">
                  <div className="budget-slider-track">
                    <div
                      className="budget-slider-fill"
                      style={{ left: `${budgetMinPct}%`, width: `${budgetMaxPct - budgetMinPct}%` }}
                    />
                    <div className="budget-slider-thumb" style={{ left: `${budgetMaxPct}%` }} />
                    <input
                      type="range"
                      className="budget-slider-input"
                      min={budgetFloor}
                      max={budgetCeiling}
                      step="500"
                      value={brief.budgetMax}
                      onChange={handleRange}
                      aria-label="Maximum budget"
                    />
                  </div>
                  <div className="budget-readout">
                    <span>{budgetSymbol}{budgetFloor.toLocaleString()}</span>
                    <strong>{getBudgetText()}</strong>
                    <span>{budgetSymbol}{budgetCeiling.toLocaleString()}</span>
                  </div>
                </div>
              </div>
              <div className="field budget-field-max">
                <label>Max</label>
                <input
                  className="input mono"
                  type="text"
                  value={`${budgetSymbol}${brief.budgetMax.toLocaleString()}`}
                  readOnly
                />
              </div>
            </div>
            <div className="currency-row">
              <span className="lbl">Currency</span>
              <div className="seg">
                <button type="button" className={brief.currency === 'USD' ? 'on' : ''} onClick={() => setCurrency('USD')}>USD $</button>
                <button type="button" className={brief.currency === 'BDT' ? 'on' : ''} onClick={() => setCurrency('BDT')}>BDT ৳</button>
              </div>
            </div>
          </section>

          {/* Platforms */}
          <section className="section">
            <div className="section-head"><span className="num">4</span><h2>Preferred platforms</h2><span className="desc">Pick one or more.</span></div>
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
            {fieldErrors.platforms ? <span className="hint" style={{ color: 'var(--coral)' }}>{fieldErrors.platforms}</span> : null}
          </section>

          <section className="section">
            <div className="section-head"><span className="num">4b</span><h2>Scoring weights</h2><span className="desc">Tune how much each trust signal matters.</span></div>
            <WeightSliders value={weights} onChange={setWeights} />
          </section>

          {/* Tier */}
          <section className="section">
            <div className="section-head"><span className="num">5</span><h2>Influencer tier</h2><span className="desc">Where you&apos;d like us to focus.</span></div>
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

          {/* Footer */}
          <div className="form-foot">
            <div className="meta">
              <span className="dot"></span>
              {!canSubmitBrief && activeDraftId
                ? 'This campaign has finished. Use Rerun search or Edit & rerun in the preview panel.'
                : activeDraftId
                  ? 'Editing saved draft'
                  : 'Save a draft to continue later'}
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button type="button" className="btn btn-ghost" onClick={() => void handleSaveDraft()} disabled={savingDraft || loading || !canSubmitBrief}>
                {savingDraft ? 'Saving…' : 'Save draft'}
              </button>
              <button type="button" className="btn btn-primary btn-lg" onClick={handleFindMatches} disabled={!canSubmitBrief || loading || savingDraft}>
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
          <div className="row"><span className="k">Description</span><span className="v">{brief.description || '—'}</span></div>
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
          {activeDraftId ? (
            <div className="preview-actions">
              <CampaignBriefActions
                campaignId={activeDraftId}
                status={activeCampaignStatus}
                label={activeCampaignLabel || brief.description || 'this campaign'}
                showEdit={false}
              />
            </div>
          ) : null}
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
