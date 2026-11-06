/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        apple: {
          bg: "#0d0e12",
          sidebar: "#14151b",
          card: "#191b24",
          cardHover: "#20232f",
          border: "rgba(255, 255, 255, 0.08)",
          textPrimary: "#f3f4f6",
          textSecondary: "#9ca3af",
          textTertiary: "#6b7280",
          blue: "#0a84ff",
          blueHover: "#2894ff",
          green: "#32d74b",
          amber: "#ff9f0a",
          coral: "#ff453a",
          purple: "#bf5af2",
        }
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"SF Pro Display"',
          '"SF Pro Text"',
          '"PingFang SC"',
          '"Microsoft YaHei UI"',
          '"Segoe UI"',
          "sans-serif"
        ]
      },
      boxShadow: {
        'apple-card': '0 4px 20px -2px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.07)',
        'apple-glow-green': '0 0 16px -2px rgba(50, 215, 75, 0.35)',
        'apple-glow-blue': '0 0 16px -2px rgba(10, 132, 255, 0.35)',
        'apple-glow-amber': '0 0 16px -2px rgba(255, 159, 10, 0.35)',
        'apple-glow-coral': '0 0 16px -2px rgba(255, 69, 58, 0.35)',
      }
    },
  },
  plugins: [],
}
