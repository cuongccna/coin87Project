export function Badge({ children, variant = "neutral" }: { children: React.ReactNode, variant?: "strong" | "moderate" | "weak" | "neutral" }) {
  const styles = {
    strong: "bg-surface_highlight text-strong border-strong/20",
    moderate: "bg-surface_highlight text-moderate border-moderate/20",
    weak: "bg-surface_highlight text-weak border-weak/20",
    neutral: "bg-surface_highlight text-tertiary border-tertiary/20"
  }

  return (
    <span className={`px-2 py-0.5 text-xxs font-medium uppercase tracking-wider border rounded-sm ${styles[variant]}`}>
      {children}
    </span>
  )
}

export function Card({ children, className = "" }: { children: React.ReactNode, className?: string }) {
  return (
    <div className={`bg-surface border border-border p-4 ${className}`}>
      {children}
    </div>
  )
}
