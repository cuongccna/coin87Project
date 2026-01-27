'use client';

/*
 * COMPONENT: Onboarding Screen
 * ----------------------------
 * DESIGN RATIONALE (MANIFESTO LOCK):
 * 
 * 1. Purpose: Mental Model Setting.
 *    - NOT marketing. NOT login.
 *    - Explains what Coin87 is NOT (news, trading, signals).
 * 
 * 2. Visuals:
 *    - Text-only hierarchy.
 *    - No distractions.
 *    - Single action.
 */

interface OnboardingScreenProps {
  onComplete: () => void;
}

export function OnboardingScreen({ onComplete }: OnboardingScreenProps) {
  return (
    <div className="fixed inset-0 z-[100] bg-background flex flex-col items-center justify-center p-8 text-center animate-in fade-in duration-500">
      
      <div className="max-w-md flex flex-col h-full justify-center">
        
        {/* Title */}
        <h1 className="text-2xl font-semibold text-primary mb-12 leading-tight tracking-tight">
          Coin87 helps you trust information,
          <span className="block text-secondary mt-1">not react to it.</span>
        </h1>

        {/* Body Points */}
        <ul className="space-y-6 text-left mb-16 mx-auto max-w-xs">
          <li className="flex gap-4">
             <span className="text-tertiary text-sm mt-0.5">•</span>
             <p className="text-sm text-secondary leading-relaxed">
               We evaluate crypto information reliability over time
             </p>
          </li>
          <li className="flex gap-4">
             <span className="text-tertiary text-sm mt-0.5">•</span>
             <p className="text-sm text-secondary leading-relaxed">
               We suppress noise and repeated rumors
             </p>
          </li>
          <li className="flex gap-4">
             <span className="text-tertiary text-sm mt-0.5">•</span>
             <p className="text-sm text-secondary leading-relaxed">
               We do not predict prices or give trading advice
             </p>
          </li>
        </ul>

        {/* Expectation Statement */}
        <p className="text-xs text-tertiary mb-12 italic">
          If there is nothing reliable, Coin87 shows nothing.
        </p>

        {/* Primary Action */}
        <button
          onClick={onComplete}
          className="w-full bg-primary text-background font-medium py-3.5 rounded-md hover:opacity-90 active:scale-[0.98] transition-all touch-manipulation"
        >
          Enter Coin87
        </button>

      </div>
    </div>
  );
}
