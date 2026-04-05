import type { Config } from "tailwindcss";

const preset: Partial<Config> = {
  theme: {
    extend: {
      colors: {
        primary: "#0037b0",
        "primary-container": "#1d4ed8",
        surface: "#f7f9fb",
        "surface-container-low": "#f2f4f6",
        "surface-container-lowest": "#ffffff",
        "surface-container-high": "#e6e8ea",
        "on-surface": "#191c1e",
        "on-surface-variant": "#434655",
        "outline-variant": "#c4c5d7",
      },
      fontFamily: {
        headline: ["Manrope", "sans-serif"],
        body: ["Inter", "sans-serif"],
      },
      borderRadius: {
        md: "12px",
        lg: "16px",
        xl: "24px",
      },
      boxShadow: {
        ambient: "0 4px 40px rgba(0, 55, 176, 0.05)",
      },
    },
  },
};

export default preset;
