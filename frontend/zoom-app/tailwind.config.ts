import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      width: {
        panel: "320px",
      },
      colors: {
        ink: "#10212f",
        mist: "#eef5f3",
        accent: "#2e8b57",
        amber: "#f7c66b",
        danger: "#f36d6d"
      },
      boxShadow: {
        soft: "0 18px 40px rgba(16, 33, 47, 0.18)"
      }
    }
  },
  plugins: []
} satisfies Config;
