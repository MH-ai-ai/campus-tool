/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: {
          base: "#eef2f7",
          subtle: "#e6ebf3",
        },
        surface: {
          card: "rgba(255, 255, 255, 0.74)",
          sidebar: "rgba(247, 249, 253, 0.80)",
          inset: "rgba(238, 242, 248, 0.66)",
          elevated: "rgba(255, 255, 255, 0.94)",
        },
        ink: {
          primary: "#18202c",
          secondary: "#526075",
          tertiary: "#7b8798",
        },
        accent: {
          DEFAULT: "#2b5797",
          hover: "#22477d",
          active: "#1b3b68",
        },
        status: {
          success: "#1f7a53",
          warning: "#9a5b13",
          danger: "#b43a40",
        },
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
          "sans-serif",
        ],
      },
      boxShadow: {
        "glass-card":
          "0 1px 2px rgba(20, 32, 51, 0.04), 0 10px 26px -10px rgba(20, 32, 51, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.92)",
        "glass-elevated":
          "0 4px 12px rgba(20, 32, 51, 0.08), 0 18px 36px -12px rgba(20, 32, 51, 0.14), inset 0 1px 0 rgba(255, 255, 255, 0.96)",
      },
    },
  },
  plugins: [],
};
