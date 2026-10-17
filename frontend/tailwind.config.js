/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)", surface: "var(--surface)", border: "var(--border)", text: "var(--text)", muted: "var(--muted)",
        primary: "var(--primary)", "quote-bg": "var(--quote-bg)",
        "high-bg": "var(--high-bg)", "high-fg": "var(--high-fg)", "high-line": "var(--high-line)",
        "med-bg": "var(--med-bg)", "med-fg": "var(--med-fg)", "med-line": "var(--med-line)",
        "low-bg": "var(--low-bg)", "low-fg": "var(--low-fg)",
      },
      fontFamily: { sans: ["IBM Plex Sans", "system-ui", "sans-serif"], mono: ["IBM Plex Mono", "monospace"],
        serif: ["Source Serif 4", "Georgia", "serif"] },
      borderRadius: { DEFAULT: "6px", lg: "8px" },
    },
  },
  plugins: [],
};
