import { SideNav } from "./SideNav";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="flex">
        <SideNav />
        <main className="flex-1 px-6 py-6">
          {/* Mobile/Tablet: intentionally minimal. Navigation can be added later if required,
              but keep interaction surface small. */}
          {children}
        </main>
      </div>
    </div>
  );
}

