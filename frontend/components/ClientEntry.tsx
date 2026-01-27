'use client';

import { useEffect, useState } from 'react';
import { OnboardingScreen } from './onboarding/OnboardingScreen';

const ONBOARDING_STORAGE_KEY = 'coin87_onboarding_completed';

export function ClientEntry({ children }: { children: React.ReactNode }) {
  const [hasCompletedOnboarding, setHasCompletedOnboarding] = useState<boolean | null>(null);

  useEffect(() => {
    // Check local storage on mount
    const stored = localStorage.getItem(ONBOARDING_STORAGE_KEY);
    setHasCompletedOnboarding(stored === 'true');
  }, []);

  const handleComplete = () => {
    localStorage.setItem(ONBOARDING_STORAGE_KEY, 'true');
    setHasCompletedOnboarding(true);
  };

  // Prevent flash of content: show nothing until check is done
  if (hasCompletedOnboarding === null) {
    return null; // Or a minimal calm background if desired
  }

  // Show onboarding if not completed
  if (!hasCompletedOnboarding) {
    return <OnboardingScreen onComplete={handleComplete} />;
  }

  // Show app content if completed
  return (
    <>
      {children}
    </>
  );
}
