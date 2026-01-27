type SkeletonProps = {
  className?: string;
  variant?: "text" | "circular" | "rectangular";
};

export function Skeleton({ className = "", variant = "rectangular" }: SkeletonProps) {
  const variantClasses = variant === "circular" ? "rounded-full" : "rounded";

  return (
    <div
      className={["skeleton", variantClasses, className].join(" ")}
      aria-hidden="true"
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="rounded-lg border border-border bg-panel p-4 shadow-soft">
      <Skeleton className="mb-2 h-4 w-24" />
      <Skeleton className="mb-1 h-3 w-full" />
      <Skeleton className="h-3 w-3/4" />
    </div>
  );
}
