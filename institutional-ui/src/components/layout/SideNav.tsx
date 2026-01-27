import Link from "next/link";

type NavItem = {
  href: string;
  label: string;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Decision Environment" },
  { href: "/decision-risks", label: "Active Decision Risks" },
  { href: "/narratives", label: "Narrative Contamination" },
  { href: "/ic-prep", label: "IC Preparation Mode" },
  { href: "/memory", label: "Institutional Memory" },
  { href: "/governance", label: "Governance / Audit" },
];

export function SideNav() {
  return (
    <nav
      aria-label="Primary navigation"
      className="hidden lg:flex lg:flex-col lg:w-72 lg:min-h-screen lg:border-r lg:border-slate-800 lg:bg-slate-950"
    >
      <div className="px-6 py-5 border-b border-slate-800">
        <div className="text-sm font-semibold tracking-wide text-slate-100">
          coin87
        </div>
        <div className="mt-1 text-xs text-slate-400">
          Decision Risk Infrastructure (read-only)
        </div>
      </div>

      <div className="px-3 py-3">
        {NAV_ITEMS.map((it) => (
          <Link
            key={it.href}
            href={it.href}
            className="block rounded-md px-3 py-2 text-sm text-slate-200 hover:bg-slate-900 hover:text-slate-100"
          >
            {it.label}
          </Link>
        ))}
      </div>

      <div className="mt-auto px-6 py-4 text-xs text-slate-500 border-t border-slate-800">
        No trading signals. No recommendations.
      </div>
    </nav>
  );
}

