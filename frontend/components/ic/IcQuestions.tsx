const QUESTIONS: string[] = [
  "What evidence would change DELAY → REVIEW today?",
  "Are we reacting to consensus optics rather than verified facts?",
  "Which decision can be deferred without breaching governance discipline?",
  "What would we write in a post-mortem if this narrative proves false?",
  "What is our explicit stop condition for continuing discussion on this topic?",
];

export function IcQuestions() {
  return (
    <div className="rounded-lg border border-border bg-bg/30 p-4">
      <ol className="list-decimal space-y-2 pl-5" aria-label="IC questions">
        {QUESTIONS.map((q) => (
          <li key={q} className="text-sm text-muted">
            {q}
          </li>
        ))}
      </ol>
      <div className="mt-3 text-xs text-muted">
        This section is static by design (no interactivity).
      </div>
    </div>
  );
}

