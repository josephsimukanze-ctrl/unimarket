/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",          // top-level templates
    "./*/templates/**/*.html",        // app-specific templates
    "./static/**/*.js",               // any JS that toggles classes
  ],

  theme: {
    extend: {
      colors: {
        // Custom palette used across the app — MUST match base.html
        ink: {
          50:  "#f8fafc",
          100: "#f1f5f9",
          200: "#e2e8f0",
          300: "#cbd5e1",
          400: "#94a3b8",
          500: "#64748b",
          600: "#475569",
          700: "#334155",
          800: "#1e293b",
          900: "#0f172a",
        },
        // Brand (blue) — used in some pages
        brand: {
          50:  "#f0f9ff",
          100: "#e0f2fe",
          200: "#bae6fd",
          300: "#7dd3fc",
          400: "#38bdf8",
          500: "#0ea5e9",
          600: "#0284c7",
          700: "#0369a1",
          800: "#075985",
          900: "#0c4a6e",
        },
        // Orange accent — used extensively (UniMarket primary)
        // If you want `bg-orange-500` etc., this is already default Tailwind.
        // Only extend if you want to alias e.g. `bg-primary-500`.
        primary: {
          50:  "#fff7ed",
          100: "#ffedd5",
          200: "#fed7aa",
          300: "#fdba74",
          400: "#fb923c",
          500: "#f97316",
          600: "#ea580c",
          700: "#c2410c",
          800: "#9a3412",
          900: "#7c2d12",
        },
      },

      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },

      boxShadow: {
        card: "0 1px 3px 0 rgb(0 0 0 / 0.05), 0 1px 2px -1px rgb(0 0 0 / 0.05)",
        "card-hover": "0 4px 12px 0 rgb(0 0 0 / 0.08)",
      },

      borderRadius: {
        xl: "0.75rem",
        "2xl": "1rem",
      },

      maxWidth: {
        "7xl": "80rem",
      },

      // Small typography nudges useful for dashboards
      fontSize: {
        "2xs": ["0.65rem", { lineHeight: "1rem" }],
      },
    },
  },

  plugins: [],
};