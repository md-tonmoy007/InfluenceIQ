"use client";

import { useEffect } from "react";

export default function LandingInteractions() {
  useEffect(() => {
    /* ── 1. Hero typewriter (#typed) ── */
    (function heroTypewriter() {
      const el = document.getElementById("typed");
      if (!el) return;
      const text =
        "Sustainable activewear for women 25\u201334, mid-tier creators, US + Canada, prioritize Pilates & running communities";
      let i = 0;
      function tick() {
        if (i <= text.length) {
          if (el) el.textContent = text.slice(0, i);
          i++;
          setTimeout(tick, i < 30 ? 22 : 14);
        }
      }
      setTimeout(tick, 350);
    })();

    /* ── 2. Marquee logos (duplicated for seamless loop) ── */
    (function marqueePopulate() {
      const track = document.getElementById("marquee-track");
      if (!track) return;
      const items = [
        "Northwind",
        "Hatch & Co.",
        "Vermeer",
        "Lumen Labs",
        "Foundry",
        "Oakridge",
        "Crestwood",
        "Aperture",
        "Halcyon",
        "Meridian",
      ];
      const html = items
        .map((n) => `<span class="logo-item"><span class="gl"></span>${n}</span>`)
        .join("");
      track.innerHTML = html + html; // duplicate for seamless scroll
    })();

    /* ── 3. Animated count-up for .count-up elements ── */
    function runCountUps() {
      const els = document.querySelectorAll<HTMLElement>(".count-up");
      els.forEach((el) => {
        if (el.dataset.done === "1") return;
        el.dataset.done = "1";
        const target = parseFloat(el.dataset.target ?? "0");
        const dec = parseInt(el.dataset.decimals ?? "0", 10);
        const dur = 1100;
        const start = performance.now();
        function frame(now: number) {
          const t = Math.min(1, (now - start) / dur);
          const eased = 1 - Math.pow(1 - t, 3);
          const v = target * eased;
          el.textContent = v.toFixed(dec);
          if (t < 1) requestAnimationFrame(frame);
          else el.textContent = target.toFixed(dec);
        }
        requestAnimationFrame(frame);
      });
    }
    runCountUps();

    /* ── 4a. Showcase typewriter (#sc-typed) ── */
    let scCleanup = false;
    (function showcaseTypewriter() {
      const target = document.getElementById("sc-typed");
      if (!target) return;
      const text =
        "Sustainable activewear for women 25\u201334, mid-tier creators, US + Canada, prioritize Pilates & running communities";
      function type() {
        if (scCleanup) return;
        if (target) target.textContent = "";
        let i = 0;
        function tick() {
          if (scCleanup) return;
          if (i <= text.length) {
            if (target) target.textContent = text.slice(0, i);
            i++;
            setTimeout(tick, i < 30 ? 22 : 14);
          } else {
            setTimeout(type, 8000);
          }
        }
        tick();
      }
      type();
    })();

    /* ── 4b. Showcase progress steps (.sp-row) loop ── */
    let spCleanup = false;
    const spTimeouts: ReturnType<typeof setTimeout>[] = [];
    (function showcaseProgress() {
      const steps = document.querySelectorAll<HTMLElement>(".sp-row");
      if (!steps.length) return;
      const timings = [550, 1200, 800, 600];
      function run() {
        if (spCleanup) return;
        steps.forEach((s) => s.classList.remove("active", "done"));
        let i = 0;
        function tick() {
          if (spCleanup) return;
          if (i > 0) {
            steps[i - 1].classList.remove("active");
            steps[i - 1].classList.add("done");
          }
          if (i < steps.length) {
            steps[i].classList.add("active");
            const id = setTimeout(tick, timings[i] ?? 700);
            spTimeouts.push(id);
            i++;
          } else {
            const id = setTimeout(run, 3000);
            spTimeouts.push(id);
          }
        }
        tick();
      }
      run();
    })();

    /* ── 5. Pricing billing toggle ── */
    const billingEl = document.getElementById("billing");
    function onBillingClick(e: Event) {
      const b = (e.target as HTMLElement).closest("button");
      if (!b) return;
      billingEl
        ?.querySelectorAll("button")
        .forEach((x) => x.classList.remove("on"));
      b.classList.add("on");
      const annual = (b as HTMLButtonElement).dataset.b === "annual";
      document
        .querySelectorAll<HTMLElement>(".price-value[data-price]")
        .forEach((v) => {
          const m = +(v.dataset.price ?? 0);
          const y = +(v.dataset.yearly ?? 0);
          const amt = v.querySelector<HTMLElement>(".amt");
          if (!amt) return;
          if (m === 0) {
            amt.textContent = "$0";
            return;
          }
          amt.style.opacity = "0";
          setTimeout(() => {
            amt.textContent = String(annual ? y : m);
            amt.style.opacity = "1";
          }, 120);
        });
    }
    billingEl?.addEventListener("click", onBillingClick);

    /* ── Cleanup ── */
    return () => {
      scCleanup = true;
      spCleanup = true;
      spTimeouts.forEach(clearTimeout);
      billingEl?.removeEventListener("click", onBillingClick);
    };
  }, []);

  return null;
}
