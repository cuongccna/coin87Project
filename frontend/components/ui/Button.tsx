type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-text text-bg hover:bg-text/90 border-transparent",
  secondary: "bg-panel text-text border-border hover:border-muted",
  ghost: "bg-transparent text-muted hover:text-text hover:bg-bg/30 border-transparent",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-2 py-1 text-xs",
  md: "px-3 py-1.5 text-sm",
  lg: "px-4 py-2 text-base",
};

export function Button({
  children,
  variant = "secondary",
  size = "md",
  className = "",
  ...props
}: {
  children: React.ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={[
        "inline-flex items-center justify-center rounded-md border font-medium transition-colors duration-150",
        "focus:outline-none focus:ring-2 focus:ring-muted focus:ring-offset-2 focus:ring-offset-bg",
        "disabled:cursor-not-allowed disabled:opacity-50",
        variantClasses[variant],
        sizeClasses[size],
        className,
      ].join(" ")}
      {...props}
    >
      {children}
    </button>
  );
}
