import type { Config } from "tailwindcss";
import preset from "@growthpilot/ui/tailwind";

const config: Config = {
  presets: [preset as Config],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
