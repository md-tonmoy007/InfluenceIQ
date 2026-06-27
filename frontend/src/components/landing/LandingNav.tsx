"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getMeOptional, type CurrentUser } from "@/lib/api";
import { routes } from "@/lib/routes";

export default function LandingNav() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    getMeOptional()
      .then((currentUser) => {
        if (active) {
          setUser(currentUser);
          setReady(true);
        }
      })
      .catch(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <header className="nav">
      <div className="nav-inner">
        <Link className="brand" href={routes.landing} aria-label="InfluenceIQ home">
          <span className="brand-mark">i</span>
          <span>InfluenceIQ</span>
        </Link>
        <nav className="nav-links">
          <a href={user ? routes.discover : "#"}>Discover</a>
          <a href="#how">How It Works</a>
          <a href="#pricing">Pricing</a>
        </nav>
        <div className="nav-cta">
          {!ready ? null : user ? (
            <>
              <Link className="signin" href={routes.settings}>
                {user.name.split(" ")[0] || "Account"}
              </Link>
              <Link className="btn btn-primary" href={routes.dashboard} id="cta-getstarted">
                Dashboard
                <span className="arrow" aria-hidden="true">&rarr;</span>
              </Link>
            </>
          ) : (
            <>
              <Link className="signin" href={routes.login}>Sign in</Link>
              <Link className="btn btn-primary" href={routes.signup} id="cta-getstarted">
                Get Started
                <span className="arrow" aria-hidden="true">&rarr;</span>
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
