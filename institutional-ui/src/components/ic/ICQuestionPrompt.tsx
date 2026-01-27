export interface ICQuestionPromptProps {
  questions: string[];
}

export function ICQuestionPrompt({ questions }: ICQuestionPromptProps) {
  const list = (questions ?? []).slice(0, 5);

  return (
    <div className="py-4 border-t border-b border-slate-800">
      <ol className="list-decimal pl-5 space-y-3" aria-label="IC discipline questions">
        {list.map((q) => (
          <li key={q} className="text-sm leading-relaxed text-slate-200">
            {q}
          </li>
        ))}
      </ol>
      <div className="mt-3 text-xs leading-relaxed text-slate-500">
        Designed to be read aloud. No checkboxes. No answers. No CTA.
      </div>
    </div>
  );
}

