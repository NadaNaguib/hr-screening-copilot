/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: "#1b3370",
          accent: "#ad7c1d",
        },
        surface: {
          page: "#F7F8FA",
          card: "#FFFFFF",
          border: "#E3E6EB",
          muted: "#6B7280",
          text: "#1F2430",
          disabled: "#C7CBD1",
        },
        semantic: {
          success: "#2F9E63",
          danger: "#C0392B",
          warning: "#D97706",
          info: "#3B5BA9",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        heading: ["Sora", "system-ui", "-apple-system", "sans-serif"],
      },
    },
  },
  plugins: [],
}
