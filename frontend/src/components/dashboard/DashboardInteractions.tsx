"use client";

import { useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { useToast } from "@/components/ui/ToastProvider";

export default function DashboardInteractions() {
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const welcomeHandled = useRef(false);

  useEffect(() => {
    /* ── 1. Animated count-up for .count-up elements ── */
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

    /* ── 2. Welcome toast ── */
    if (searchParams.get("welcome") === "1" && !welcomeHandled.current) {
      toast("Welcome to InfluenceIQ! Your account is ready.", {
        type: "success",
        duration: 4500,
      });
      welcomeHandled.current = true;
    }
  }, [searchParams, toast]);

  return null;
}
