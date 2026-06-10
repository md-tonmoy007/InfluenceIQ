'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

type Particle = {
  id: number;
  s: number;
  left: number;
  duration: number;
  delay: number;
};

export default function MatchingAnimation() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [currentStep, setCurrentStep] = useState(0);
  const [pct, setPct] = useState(0);
  const [ticker, setTicker] = useState('IIQ•MATCHING · v3');
  const [doneSteps, setDoneSteps] = useState<number[]>([]);
  const [particles, setParticles] = useState<Particle[]>([]);

  const timings = useMemo(() => [720, 600, 800, 700, 580], []);
  const tickers = useMemo(() => ['IIQ•SCANNING', 'IIQ•DEMOGRAPHICS', 'IIQ•SENTIMENT', 'IIQ•FIT', 'IIQ•RANKING'], []);
  const total = useMemo(() => timings.reduce((a, b) => a + b, 0), [timings]);

  useEffect(() => {
    // Generate particles only once on mount to keep render pure
    // Wrapping in requestAnimationFrame to avoid "cascading renders" lint error
    const handle = requestAnimationFrame(() => {
      const newParticles = [...Array(24)].map((_, i) => ({
        id: i,
        s: 1 + Math.random() * 3,
        left: Math.random() * 100,
        duration: 8 + Math.random() * 8,
        delay: -Math.random() * 8
      }));
      setParticles(newParticles);
    });
    return () => cancelAnimationFrame(handle);
  }, []);

  useEffect(() => {
    let currentElapsed = 0;
    let isMounted = true;

    const runAnimation = async () => {
      for (let i = 0; i < timings.length; i++) {
        if (!isMounted) break;
        setCurrentStep(i);
        setTicker(`${tickers[i]} · v3`);
        
        const dur = timings[i];
        const start = currentElapsed;
        
        await new Promise<void>(resolve => {
          const startTime = performance.now();
          const frame = (now: number) => {
            if (!isMounted) return;
            const t = Math.min(1, (now - startTime) / dur);
            const p = ((start + dur * t) / total) * 100;
            setPct(Math.round(p));
            if (t < 1) requestAnimationFrame(frame);
            else resolve();
          };
          requestAnimationFrame(frame);
        });
        
        currentElapsed += dur;
        setDoneSteps(prev => [...prev, i]);
      }
      
      if (isMounted) {
        setPct(100);
        setTicker(`IIQ•COMPLETE · ${(Math.random() * 100 + 200).toFixed(0).padStart(3, '0')} matches`);
        
        setTimeout(() => {
          if (isMounted) {
            const campaignId = searchParams.get('campaignId');
            const next =
              searchParams.get('next') ||
              (campaignId
                ? `/shortlist?campaignId=${encodeURIComponent(campaignId)}`
                : '/shortlist');
            router.push(next);
          }
        }, 550);
      }
    };

    runAnimation();
    return () => { isMounted = false; };
  }, [router, searchParams, tickers, timings, total]);

  return (
    <>
      <div id="particles">
        {particles.map((p) => (
          <span
            key={p.id}
            className="particle"
            style={{
              width: `${p.s}px`,
              height: `${p.s}px`,
              left: `${p.left}%`,
              bottom: '-10px',
              animationDuration: `${p.duration}s`,
              animationDelay: `${p.delay}s`
            }}
          />
        ))}
      </div>

      <div className="stage">
        <div className="brand"><span className="mark">i</span><span>InfluenceIQ</span></div>

        <div className="orb">
          <div className="ring r1"></div>
          <div className="ring r2"></div>
          <div className="ring r3"></div>
          <div className="orbit"><span className="dot d1"></span><span className="dot d2"></span><span className="dot d3"></span></div>
          <div className="core"><span className="center"></span></div>
        </div>

        <h1>Finding your <span className="ac">perfect</span> creators…</h1>
        <p className="lede">Our matching model is running 5 passes over 2.41M indexed profiles. Sit tight — this takes ~4 seconds.</p>

        <div className="steps" id="steps">
          {[
            'Scanning 50,000+ influencer profiles',
            'Analyzing audience demographics',
            'Running sentiment analysis on engagement',
            'Scoring brand-audience fit',
            'Ranking your top matches'
          ].map((text, i) => (
            <div key={i} className={`step ${currentStep === i ? 'active' : ''} ${doneSteps.includes(i) ? 'done' : ''}`} data-i={i}>
              <span className="icon">
                <span className="spin-i"></span>
                <svg className="check" viewBox="0 0 11 8" fill="none" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 4 L4 7 L10 1" />
                </svg>
              </span>
              <span>{text}</span>
              <span className="meta">{doneSteps.includes(i) ? `${(timings[i] / 1000).toFixed(1)}s` : '—'}</span>
            </div>
          ))}
        </div>

        <div className="bar-wrap">
          <div className="bar"><div className="fill" style={{ width: `${pct}%` }}></div></div>
          <div className="bar-meta"><span>{ticker}</span><span className="pct"><span>{pct}</span>%</span></div>
        </div>
      </div>
    </>
  );
}
