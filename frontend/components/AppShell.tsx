import Link from "next/link";

const navLinks = [
  { href: "/ic-mode", label: "IC Preparation Mode" },
  { href: "/", label: "Decision Environment" },
  { href: "/risk-events", label: "Active Decision Risks" },
  { href: "/narratives", label: "Narrative Contamination" },
  { href: "/history", label: "Institutional Memory" },
  { href: "/governance", label: "Governance / Audit" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-bg text-text">
      <nav
        className="sticky top-0 z-10 flex flex-wrap items-center gap-4 border-b border-border bg-bg/90 px-4 py-3 backdrop-blur"
        aria-label="Primary"
      >
        <div className="text-sm font-semibold tracking-wide text-text">coin87</div>
        <div className="hidden h-4 w-px bg-border sm:block" />
        {navLinks.map((link) => (
          <Link
            key={link.href}
            className="text-xs text-muted transition-colors hover:text-text"
            href={link.href}
          >
            {link.label}
          </Link>
        ))}
        <div className="ml-auto text-xs text-muted">Read-only. No trade signals.</div>
      </nav>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}

