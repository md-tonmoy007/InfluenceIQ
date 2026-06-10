"use client";

import React from "react";
import AuthGate from "@/components/auth/AuthGate";
import OnboardingStepper from "@/components/ui/OnboardingStepper";
import "../onboarding.css";

export default function OnboardingPage() {
  return <AuthGate>{() => <OnboardingStepper />}</AuthGate>;
}
