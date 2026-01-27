/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    fontFamily: {
      sans: ['Inter', 'system-ui', 'sans-serif'],
      mono: ['JetBrains Mono', 'monospace'],
    },
    extend: {
      colors: {
        // Calm, sparse, authoritative palette
        background: "#09090b", // Zinc 950
        surface: "#18181b",    // Zinc 900
        surface_highlight: "#27272a", // Zinc 800
        
        border: "#27272a",     // Zinc 800
        
        primary: "#e4e4e7",    // Zinc 200 (Main Text)
        secondary: "#a1a1aa",  // Zinc 400 (Secondary Text)
        tertiary: "#52525b",   // Zinc 600 (Meta info)
        
        // Semantic (Non-alert)
        strong: "#f4f4f5",     // Zinc 100 (High reliability)
        moderate: "#d4d4d8",   // Zinc 300
        weak: "#71717a",       // Zinc 500
        suppressed: "#3f3f46", // Zinc 700
      },
      fontSize: {
        xxs: '0.625rem',
      },
      boxShadow: {
        soft: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
      },
    },
  },
  plugins: [],
};

