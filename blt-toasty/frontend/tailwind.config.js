/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: '#E10101',
        'brand-hover': '#b91c1c',
        'neutral-border': '#E5E5E5',
        'dark-base': '#111827',
        'dark-surface': '#1F2937',
        'blt-footer': '#0e0d0c',
        'nav-active': '#feeae9',
      },
      fontFamily: {
        sans: ['Manrope', 'ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Consolas', 'monospace'],
      },
      boxShadow: {
        card: '0 10px 30px rgba(17, 24, 39, 0.07)',
        soft: '0 1px 2px rgba(17, 24, 39, 0.04)',
        float: '0 10px 24px -18px rgba(220, 38, 38, 0.8)',
        'focus-brand': '0 0 0 2px rgba(225, 1, 1, 0.24)',
      },
      animation: {
        'pulse-indicator': 'indicator-pulse 2s infinite',
        'spin-slow': 'blt-spin 1s linear infinite',
      },
      keyframes: {
        'indicator-pulse': {
          '0%': { boxShadow: '0 0 0 0 rgba(225, 1, 1, 0.45)' },
          '70%': { boxShadow: '0 0 0 9px rgba(225, 1, 1, 0)' },
          '100%': { boxShadow: '0 0 0 0 rgba(225, 1, 1, 0)' },
        },
        'blt-spin': {
          to: { transform: 'rotate(360deg)' },
        },
      },
      borderRadius: {
        '4xl': '2rem',
      },
    },
  },
  plugins: [],
};
