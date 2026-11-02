import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: { background: "#080c14", surface: "rgba(15, 23, 42, 0.65)" }
    }
  },
  plugins: [],
};
export default config;
