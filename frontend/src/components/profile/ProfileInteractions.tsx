'use client';

import React, { useState } from 'react';
import SaveToListPopover from '@/components/ui/SaveToListPopover';
import { useToast } from '@/components/ui/ToastProvider';

export default function ProfileInteractions() {
  // ROI estimator state
  const followers = 341000;
  const reachBase = 0.4 * followers;
  const [budgetRaw, setBudgetRaw] = useState('2,400');
  const [reach, setReach] = useState('196K');
  const [engagement, setEngagement] = useState('12.2K');
  const [cpe, setCpe] = useState('0.20');

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const { toast } = useToast();

  const fmtK = (n: number) => {
    if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(n >= 1e4 ? 0 : 1) + 'K';
    return Math.round(n).toString();
  };

  const recompute = (rawBudget: string) => {
    const raw = rawBudget.replace(/[^0-9.]/g, '');
    const budget = parseFloat(raw) || 0;
    const boost = Math.min(2.4, 1 + budget / 1800);
    const calculatedReach = Math.round(reachBase * boost);
    const calculatedEng = Math.round(calculatedReach * 0.062);
    const calculatedCpe = calculatedEng > 0 ? budget / calculatedEng : 0;

    setReach(fmtK(calculatedReach));
    setEngagement(fmtK(calculatedEng));
    setCpe(calculatedCpe.toFixed(2));
  };

  const handleBudgetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.replace(/[^0-9]/g, '');
    if (raw) {
      const formatted = parseInt(raw, 10).toLocaleString('en-US');
      setBudgetRaw(formatted);
      recompute(raw);
    } else {
      setBudgetRaw('');
      recompute('0');
    }
  };

  const openModal = () => {
    setIsModalOpen(true);
    document.body.style.overflow = 'hidden';
  };

  const closeModal = () => {
    setIsModalOpen(false);
    document.body.style.overflow = '';
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    closeModal();
    toast(
      <>
        Message queued for <span style={{ fontFamily: 'Instrument Serif, serif', fontStyle: 'italic' }}>Lila Park</span> · we&apos;ll notify you on reply.
      </>,
      { type: 'success', duration: 4200 }
    );
  };

  return (
    <>
      {/* ROI Estimator */}
      <section className="panel">
        <div className="panel-head">
          <h3>
            <span className="pin"></span>ROI Estimator
          </h3>
          <span className="meta">Estimates · adjust budget to recalculate</span>
        </div>
        <div className="roi-grid">
          <div className="roi-cell input">
            <div className="lbl">Campaign Budget</div>
            <div className="roi-input">
              <span className="currency">$</span>
              <input id="roi-budget" type="text" inputMode="numeric" value={budgetRaw} onChange={handleBudgetChange} />
            </div>
          </div>
          <div className="roi-cell">
            <div className="lbl">Est. Reach</div>
            <div className="val">
              <span id="roi-reach">{reach}</span>
            </div>
          </div>
          <div className="roi-cell engagement">
            <div className="lbl">Est. Engagement</div>
            <div className="val">
              <span id="roi-eng">{engagement}</span>
            </div>
          </div>
          <div className="roi-cell cpe">
            <div className="lbl">Cost / Engagement</div>
            <div className="val">
              $<span id="roi-cpe">{cpe}</span>
            </div>
          </div>
        </div>
      </section>

      {/* Actions */}
      <div className="actions-row">
        <div style={{ position: 'relative' }}>
          <SaveToListPopover>
            <button className="btn btn-ghost" id="save-btn" type="button">
              <svg className="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                <path d="M19 21l-7-4.5L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16Z" />
              </svg>
              Save to Campaign List
            </button>
          </SaveToListPopover>
        </div>
        <button className="btn btn-primary" id="contact-btn" type="button" onClick={openModal}>
          Contact This Influencer
          <span className="arrow">→</span>
        </button>
      </div>

      {/* Contact Modal */}
      {isModalOpen && (
        <div
          id="contact-modal"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(10,11,16,0.55)',
            backdropFilter: 'blur(6px)',
            zIndex: 300,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
            animation: 'fadeIn .25s ease',
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) closeModal();
          }}
        >
          <div
            style={{
              background: '#fff',
              borderRadius: '18px',
              width: '100%',
              maxWidth: '520px',
              overflow: 'hidden',
              boxShadow: '0 40px 80px -20px rgba(60,50,120,0.4)',
              animation: 'popIn .35s cubic-bezier(.2,.8,.2,1)',
            }}
          >
            <div
              style={{
                position: 'relative',
                padding: '22px 24px',
                background:
                  'radial-gradient(360px 160px at 80% -40%,oklch(0.94 0.05 30 / 0.7),transparent 60%),radial-gradient(360px 160px at 0% 120%,oklch(0.94 0.05 285 / 0.7),transparent 60%)',
                borderBottom: '1px solid var(--line-soft)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <div className="pfp" style={{ width: '44px', height: '44px', fontSize: '14px', boxShadow: '0 0 0 2px #fff, 0 0 0 3px var(--line)', margin: 0 }}>
                  LP
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '11px', fontFamily: "'JetBrains Mono',monospace", letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--muted)' }}>
                    New outreach
                  </div>
                  <div style={{ fontSize: '17px', fontWeight: 500, letterSpacing: '-0.012em', marginTop: '2px' }}>
                    Contact <span style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontStyle: 'italic' }}>Lila Park</span>
                  </div>
                </div>
                <button
                  id="modal-close"
                  type="button"
                  onClick={closeModal}
                  style={{
                    width: '32px',
                    height: '32px',
                    border: 0,
                    background: 'rgba(255,255,255,0.6)',
                    borderRadius: '8px',
                    display: 'grid',
                    placeItems: 'center',
                    color: 'var(--muted)',
                    cursor: 'pointer',
                  }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <path d="M6 6l12 12M18 6L6 18" />
                  </svg>
                </button>
              </div>
            </div>

            <form id="contact-form" style={{ padding: '22px 24px', display: 'flex', flexDirection: 'column', gap: '14px' }} onSubmit={handleSubmit}>
              <div style={{ display: 'flex', gap: '8px' }}>
                <label
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    border: '1px solid var(--line)',
                    borderRadius: '9px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '12.5px',
                    color: 'var(--ink-soft)',
                    cursor: 'pointer',
                    background: 'linear-gradient(180deg,oklch(0.97 0.025 285),#fff)',
                  }}
                >
                  <input type="radio" name="channel" defaultChecked style={{ accentColor: 'var(--violet)' }} />
                  <span
                    style={{
                      width: '20px',
                      height: '20px',
                      borderRadius: '6px',
                      background: 'linear-gradient(135deg,var(--violet),var(--coral))',
                      display: 'grid',
                      placeItems: 'center',
                      color: '#fff',
                    }}
                  >
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.7">
                      <rect x="3" y="5" width="18" height="14" rx="2" />
                      <path d="m3 7 9 6 9-6" />
                    </svg>
                  </span>
                  Email
                </label>
                <label
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    border: '1px solid var(--line)',
                    borderRadius: '9px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '12.5px',
                    color: 'var(--ink-soft)',
                    cursor: 'pointer',
                  }}
                >
                  <input type="radio" name="channel" style={{ accentColor: 'var(--violet)' }} />
                  <span
                    style={{
                      width: '20px',
                      height: '20px',
                      borderRadius: '6px',
                      background: 'linear-gradient(135deg,#f58529,#dd2a7b 50%,#8134af 80%,#515bd4)',
                      display: 'grid',
                      placeItems: 'center',
                      color: '#fff',
                    }}
                  >
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.7">
                      <rect x="3" y="3" width="18" height="18" rx="5" />
                      <circle cx="12" cy="12" r="4" />
                    </svg>
                  </span>
                  Instagram DM
                </label>
              </div>

              <div>
                <label
                  style={{
                    display: 'block',
                    fontSize: '11.5px',
                    fontFamily: "'JetBrains Mono',monospace",
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    color: 'var(--muted)',
                    marginBottom: '6px',
                  }}
                >
                  Campaign
                </label>
                <div className="select-wrap" style={{ position: 'relative' }}>
                  <select
                    className="select"
                    style={{
                      width: '100%',
                      height: '40px',
                      padding: '0 36px 0 12px',
                      border: '1px solid var(--line)',
                      borderRadius: '9px',
                      background: '#fff',
                      fontSize: '14px',
                      appearance: 'none',
                      WebkitAppearance: 'none',
                      cursor: 'pointer',
                    }}
                  >
                    <option>SS26 Trail Capsule — Product Launch</option>
                    <option>Ramadan Campaign 2026 — Awareness</option>
                    <option>Holiday gifting (US + UK) — Sales</option>
                  </select>
                </div>
              </div>

              <div>
                <label
                  style={{
                    display: 'block',
                    fontSize: '11.5px',
                    fontFamily: "'JetBrains Mono',monospace",
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    color: 'var(--muted)',
                    marginBottom: '6px',
                  }}
                >
                  Subject
                </label>
                <input
                  id="contact-subject"
                  style={{ width: '100%', height: '40px', padding: '0 12px', border: '1px solid var(--line)', borderRadius: '9px', background: '#fff', fontSize: '14px', outline: 'none' }}
                  defaultValue="Collab idea — Northwind SS26 capsule + your K-beauty audience"
                />
              </div>

              <div>
                <label
                  style={{
                    display: 'block',
                    fontSize: '11.5px',
                    fontFamily: "'JetBrains Mono',monospace",
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    color: 'var(--muted)',
                    marginBottom: '6px',
                  }}
                >
                  Message
                </label>
                <textarea
                  id="contact-message"
                  rows={5}
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '1px solid var(--line)',
                    borderRadius: '9px',
                    background: '#fff',
                    fontSize: '14px',
                    outline: 'none',
                    resize: 'vertical',
                    fontFamily: 'inherit',
                    lineHeight: 1.5,
                  }}
                  defaultValue={`Hi Lila,\n\nI'm Elena from Northwind Outdoor. We're launching our SS26 Trail capsule and your ingredient-led storytelling feels like a perfect match for our audience.\n\nOpen to discussing a 2-post Reels collab in the $1,800–$2,600 range, with full creative control on your side. Would love to chat — would the week of May 19 work?\n\n— Elena`}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', paddingTop: '6px' }}>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', fontSize: '12.5px', color: 'var(--muted)' }}>
                  <input type="checkbox" defaultChecked style={{ accentColor: 'var(--violet)' }} />
                  Track opens &amp; replies
                </label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    type="button"
                    id="modal-cancel"
                    onClick={closeModal}
                    style={{ height: '38px', padding: '0 16px', border: '1px solid var(--line)', borderRadius: '9px', background: '#fff', fontSize: '13px', color: 'var(--ink)', cursor: 'pointer', fontFamily: 'inherit' }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    id="modal-send"
                    style={{
                      height: '38px',
                      padding: '0 18px',
                      border: 0,
                      borderRadius: '9px',
                      background: 'linear-gradient(180deg,var(--violet),oklch(0.50 0.22 285))',
                      color: '#fff',
                      fontSize: '13px',
                      fontWeight: 500,
                      cursor: 'pointer',
                      fontFamily: 'inherit',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      boxShadow: '0 6px 16px -6px rgba(120,80,255,0.45)',
                    }}
                  >
                    Send message <span style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontStyle: 'italic' }}>→</span>
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
