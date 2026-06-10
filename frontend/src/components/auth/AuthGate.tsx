"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { getMe, type CurrentUser } from "@/lib/api";

type AuthGateProps = {
  children: (user: CurrentUser) => ReactNode;
};

export default function AuthGate({ children }: AuthGateProps) {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let active = true;
    getMe()
      .then((currentUser) => {
        if (active) {
          setUser(currentUser);
          setChecking(false);
        }
      })
      .catch(() => {
        if (active) {
          router.replace("/login");
        }
      });
    return () => {
      active = false;
    };
  }, [router]);

  if (checking || !user) {
    return null;
  }

  return <>{children(user)}</>;
}
