/** Tailwind is compiled once into public/_home/home.css (npm run build:css); no CDN at runtime. */
module.exports = {
  content: ["./public/index.html", "./public/_home/home.js"],
  // home.js builds "heat-" + level at runtime, so the scanner cannot see these names.
  safelist: ["heat-0", "heat-1", "heat-2", "heat-3", "heat-4", "heat-now"],
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
