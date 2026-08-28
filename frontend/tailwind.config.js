/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        jee: {
          dark: "#0b0f19",
          card: "#111827",
          border: "#1f2937",
          physics: "#6366f1",
          chemistry: "#10b981",
          math: "#f59e0b",
          accent: "#3b82f6",
        },
      },
    },
  },
  plugins: [],
}
