/** Tailwind is compiled once into public/_home/home.css (npm run build:css); no CDN at runtime. */
module.exports = {
  content: ["./public/index.html", "./public/_home/home.js"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      },
    },
  },
};
