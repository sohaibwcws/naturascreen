import type { Config } from "tailwindcss";

// Dark scientific theme (PRD §8): high contrast, restrained palette, data-forward.
// Cell-state hues are the single source of truth shared by the 3D view and charts.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: {
          900: "#080b10", // app background
          850: "#0c1118",
          800: "#11161f", // panels
          750: "#161c27",
          700: "#1c2430", // borders / hover
        },
        ink: {
          DEFAULT: "#e6edf6",
          muted: "#9aa7b8",
          faint: "#5f6b7c",
        },
        accent: {
          DEFAULT: "#3fd0c9", // clinical teal
          dim: "#2a8f8a",
        },
        // Cell states — shared with the WebGL view.
        cell: {
          dividing: "#46d98a",
          stressed: "#f2b134",
          dying: "#f2603c",
          dead: "#5a6472",
        },
        warn: "#f2b134",
        danger: "#f2603c",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255,255,255,0.03) inset, 0 8px 24px -12px rgba(0,0,0,0.6)",
      },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "pulse-soft": { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.55" } },
      },
      animation: {
        "fade-in": "fade-in 0.3s ease-out",
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
