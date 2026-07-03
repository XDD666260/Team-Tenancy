/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#2b4b82",
        "deep-purple": "#392752",
        "pink-light": "#f7b4a7",
        "pink-soft": "#f0abc1",
        mint: "#94ddde",
        "dust-purple": {
          DEFAULT: "#6e426a",
          mid: "#a0637f",
          light: "#ce8992",
        },
        "bg-dark": "#1a1a2e",
      },
      fontFamily: {
        sans: [
          "PingFang SC",
          "Noto Sans SC",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      backgroundImage: {
        "hero-gradient":
          "linear-gradient(135deg, #1a1a2e 0%, #2b4b82 40%, #392752 100%)",
      },
      backdropBlur: {
        card: "20px",
      },
    },
  },
  plugins: [],
};
